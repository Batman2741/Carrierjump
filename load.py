import copy
import json
import logging
import os
import queue
import threading
import urllib.error
import urllib.request


PLUGIN_NAME = "ISSB"
VERSION = "1.1.0"

CONFIG_FILENAME = "config.json"
ENV_WEBHOOK_URL = "ISSB_DISCORD_WEBHOOK_URL"
DEFAULT_TIMEOUT_SECONDS = 10

_plugin_folder_name = os.path.basename(os.path.dirname(__file__)) or PLUGIN_NAME
logger = logging.getLogger(f"edmc.{_plugin_folder_name}")

_default_embed_config = {
    "username": "",
    "avatar_url": "",
    "request": {
        "title": "{carrier} jump scheduled",
        "description": "",
        "color": 3447003,
        "fields": [
            {"name": "Carrier", "value": "{carrier}", "inline": True},
            {"name": "Destination", "value": "{destination}", "inline": True},
            {"name": "Body", "value": "{body}", "inline": True},
            {"name": "Departure", "value": "{departure_time}", "inline": False},
        ],
        "footer": "Elite Dangerous",
    },
    "arrival": {
        "title": "{carrier} arrived",
        "description": "",
        "color": 5763719,
        "fields": [
            {"name": "Carrier", "value": "{carrier}", "inline": True},
            {"name": "System", "value": "{system}", "inline": True},
            {"name": "Body", "value": "{body}", "inline": True},
        ],
        "footer": "Elite Dangerous",
    },
}

_plugin_dir = None
_webhook_url = ""
_timeout_seconds = DEFAULT_TIMEOUT_SECONDS
_notify_jump_requests = True
_notify_jump_arrivals = True
_warned_missing_webhook = False
_carrier_name_override = ""
_carrier_callsign_override = ""
_embed_config = copy.deepcopy(_default_embed_config)
_carrier_cache = {}

_work_queue = None
_worker_thread = None


def plugin_start3(plugin_dir):
    """
    Load the plugin into EDMarketConnector.
    """
    global _plugin_dir

    _plugin_dir = plugin_dir
    _load_config()
    _start_worker()

    logger.info("%s %s started from %s", PLUGIN_NAME, VERSION, plugin_dir)
    return PLUGIN_NAME


def plugin_stop():
    """
    Stop the plugin and wait briefly for the Discord worker to exit.
    """
    _stop_worker()
    logger.info("%s stopped", PLUGIN_NAME)


def plugin_reload():
    """
    Reload config without requiring EDMC to restart.
    """
    _load_config()
    logger.info("%s reloaded", PLUGIN_NAME)


def journal_entry(cmdr, is_beta, system, station, entry, state):
    """
    Receive Elite Dangerous journal events from EDMarketConnector.
    """
    event = entry.get("event")

    if event in ("CarrierStats", "CarrierNameChanged", "CarrierBuy"):
        _remember_carrier(entry)
        return None

    if event == "CarrierJumpRequest" and _notify_jump_requests:
        _queue_discord_payload(_build_embed_payload("request", entry))
    elif event == "CarrierJump" and _notify_jump_arrivals:
        _queue_discord_payload(_build_embed_payload("arrival", entry))

    return None


def _load_config():
    global _webhook_url
    global _timeout_seconds
    global _notify_jump_requests
    global _notify_jump_arrivals
    global _warned_missing_webhook
    global _carrier_name_override
    global _carrier_callsign_override
    global _embed_config

    _webhook_url = os.environ.get(ENV_WEBHOOK_URL, "").strip()
    _timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    _notify_jump_requests = True
    _notify_jump_arrivals = True
    _warned_missing_webhook = False
    _carrier_name_override = ""
    _carrier_callsign_override = ""
    _embed_config = copy.deepcopy(_default_embed_config)

    config = _read_config()
    configured_webhook = str(config.get("discord_webhook_url", "")).strip()
    if configured_webhook:
        _webhook_url = configured_webhook

    _timeout_seconds = _positive_int(
        config.get("timeout_seconds"),
        DEFAULT_TIMEOUT_SECONDS,
    )
    _notify_jump_requests = _config_bool(config.get("notify_jump_requests"), True)
    _notify_jump_arrivals = _config_bool(config.get("notify_jump_arrivals"), True)
    _carrier_name_override = str(config.get("carrier_name", "")).strip()
    _carrier_callsign_override = str(config.get("carrier_callsign", "")).strip()
    _embed_config = _merge_dicts(
        copy.deepcopy(_default_embed_config),
        config.get("embed", {}),
    )

    if _carrier_name_override or _carrier_callsign_override:
        _carrier_cache["config"] = {
            "name": _carrier_name_override,
            "callsign": _carrier_callsign_override,
            "station_name": "",
        }

    if not _webhook_url:
        logger.warning(
            "%s has no Discord webhook. Set %s or add discord_webhook_url to %s.",
            PLUGIN_NAME,
            ENV_WEBHOOK_URL,
            _config_path() or CONFIG_FILENAME,
        )


def _read_config():
    config_path = _config_path()
    if not config_path or not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read %s", config_path)
        return {}

    if not isinstance(config, dict):
        logger.error("%s must contain a JSON object", config_path)
        return {}

    return config


def _config_path():
    if not _plugin_dir:
        return None
    return os.path.join(_plugin_dir, CONFIG_FILENAME)


def _positive_int(value, fallback):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback

    return parsed if parsed > 0 else fallback


def _config_bool(value, fallback):
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("1", "true", "yes", "on"):
            return True
        if normalized in ("0", "false", "no", "off"):
            return False
    return fallback


def _merge_dicts(base, override):
    if not isinstance(override, dict):
        return base

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _merge_dicts(base[key], value)
        else:
            base[key] = value
    return base


def _start_worker():
    global _work_queue
    global _worker_thread

    if _worker_thread and _worker_thread.is_alive():
        return

    _work_queue = queue.Queue()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        name=f"{PLUGIN_NAME}DiscordWorker",
        daemon=True,
    )
    _worker_thread.start()


def _stop_worker():
    global _work_queue
    global _worker_thread

    if _work_queue:
        _work_queue.put(None)

    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5)

    _work_queue = None
    _worker_thread = None


def _worker_loop():
    while True:
        item = _work_queue.get()
        try:
            if item is None:
                return
            _send_discord_payload(
                item["webhook_url"],
                item["payload"],
                item["timeout_seconds"],
            )
        finally:
            _work_queue.task_done()


def _queue_discord_payload(payload):
    global _warned_missing_webhook

    if not _webhook_url:
        if not _warned_missing_webhook:
            logger.warning("Discord webhook is not configured; notification skipped.")
            _warned_missing_webhook = True
        return

    if not _work_queue:
        logger.error("Discord worker is not running; notification skipped.")
        return

    _work_queue.put(
        {
            "webhook_url": _webhook_url,
            "payload": payload,
            "timeout_seconds": _timeout_seconds,
        }
    )


def _send_discord_payload(webhook_url, payload, timeout_seconds):
    request_body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"{PLUGIN_NAME}/{VERSION}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        logger.error("Discord webhook returned HTTP %s: %s", exc.code, _read_error(exc))
    except urllib.error.URLError as exc:
        logger.error("Could not reach Discord webhook: %s", exc.reason)
    except OSError:
        logger.exception("Discord webhook request failed")
    else:
        if 200 <= status < 300:
            logger.info("Discord carrier jump notification sent")
        else:
            logger.error("Discord webhook returned HTTP %s", status)


def _read_error(exc):
    try:
        return exc.read().decode("utf-8", errors="replace")
    except Exception:
        return str(exc)


def _remember_carrier(entry):
    carrier_id = _carrier_id(entry)
    if not carrier_id:
        return

    current = _carrier_cache.get(carrier_id, {})
    name = entry.get("Name") or entry.get("CarrierName") or current.get("name", "")
    callsign = entry.get("Callsign") or current.get("callsign", "")
    station_name = entry.get("StationName") or current.get("station_name", "")

    _carrier_cache[carrier_id] = {
        "name": str(name).strip(),
        "callsign": str(callsign).strip(),
        "station_name": str(station_name).strip(),
    }


def _build_embed_payload(kind, entry):
    values = _template_values(entry)
    embed_template = _embed_config.get(kind, {})
    embed = {
        "title": _render_template(embed_template.get("title", ""), values),
        "description": _render_template(embed_template.get("description", ""), values),
        "color": _embed_color(embed_template.get("color")),
        "fields": _embed_fields(embed_template.get("fields", []), values),
    }

    footer = _render_template(embed_template.get("footer", ""), values)
    if footer:
        embed["footer"] = {"text": footer}

    embed = {key: value for key, value in embed.items() if value not in ("", [], None)}
    payload = {"embeds": [embed]}

    username = str(_embed_config.get("username", "")).strip()
    avatar_url = str(_embed_config.get("avatar_url", "")).strip()
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    return payload


def _template_values(entry):
    carrier = _carrier_display_name(entry)
    carrier_info = _carrier_info(entry)
    destination = entry.get("SystemName") or entry.get("DestinationSystem") or ""
    system = entry.get("StarSystem") or destination

    return {
        "carrier": carrier,
        "carrier_name": carrier_info.get("name") or carrier,
        "carrier_callsign": carrier_info.get("callsign", ""),
        "carrier_id": str(_carrier_id(entry) or ""),
        "station_name": str(entry.get("StationName") or carrier_info.get("station_name") or ""),
        "destination": str(destination or "unknown destination"),
        "system": str(system or "unknown system"),
        "body": str(entry.get("Body") or "unknown body"),
        "body_id": str(entry.get("BodyID") or ""),
        "departure_time": str(entry.get("DepartureTime") or "unknown departure time"),
        "event": str(entry.get("event") or ""),
        "timestamp": str(entry.get("timestamp") or ""),
    }


def _embed_fields(fields, values):
    rendered_fields = []
    if not isinstance(fields, list):
        return rendered_fields

    for field in fields[:25]:
        if not isinstance(field, dict):
            continue

        name = _render_template(field.get("name", ""), values)
        value = _render_template(field.get("value", ""), values)
        if not name or not value:
            continue

        rendered_fields.append(
            {
                "name": name[:256],
                "value": value[:1024],
                "inline": _config_bool(field.get("inline"), False),
            }
        )

    return rendered_fields


def _embed_color(value):
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("#"):
            stripped = stripped[1:]
            try:
                return int(stripped, 16)
            except ValueError:
                return 3447003
        try:
            return int(stripped)
        except ValueError:
            return 3447003
    if isinstance(value, int):
        return value
    return 3447003


def _render_template(template, values):
    if template is None:
        return ""
    return str(template).format_map(_SafeTemplateValues(values))


def _carrier_display_name(entry):
    carrier_info = _carrier_info(entry)
    name = carrier_info.get("name", "")
    callsign = carrier_info.get("callsign", "")
    station_name = carrier_info.get("station_name", "")

    if name and callsign:
        return f"{name} ({callsign})"
    if name:
        return name
    if callsign:
        return callsign
    if station_name:
        return station_name

    carrier_id = _carrier_id(entry)
    if carrier_id:
        return f"Fleet carrier {carrier_id}"
    return "Fleet carrier"


def _carrier_info(entry):
    carrier_id = _carrier_id(entry)
    configured = _carrier_cache.get(
        "config",
        {"name": "", "callsign": "", "station_name": ""},
    )

    if carrier_id and carrier_id in _carrier_cache:
        cached = _carrier_cache[carrier_id]
        return {
            "name": configured.get("name") or cached.get("name", ""),
            "callsign": configured.get("callsign") or cached.get("callsign", ""),
            "station_name": cached.get("station_name", ""),
        }

    if configured.get("name") or configured.get("callsign"):
        return configured

    return {
        "name": str(entry.get("Name") or entry.get("CarrierName") or "").strip(),
        "callsign": str(entry.get("Callsign") or "").strip(),
        "station_name": str(entry.get("StationName") or "").strip(),
    }


def _carrier_id(entry):
    carrier_id = entry.get("CarrierID") or entry.get("MarketID")
    if carrier_id in ("", None):
        return ""
    return str(carrier_id)


class _SafeTemplateValues(dict):
    def __missing__(self, key):
        return "{" + key + "}"
