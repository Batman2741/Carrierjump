import json
import logging
import os
import queue
import threading
import urllib.error
import urllib.request


PLUGIN_NAME = "ISSB"
VERSION = "1.0.0"

CONFIG_FILENAME = "config.json"
ENV_WEBHOOK_URL = "ISSB_DISCORD_WEBHOOK_URL"
DEFAULT_TIMEOUT_SECONDS = 10

_plugin_folder_name = os.path.basename(os.path.dirname(__file__)) or PLUGIN_NAME
logger = logging.getLogger(f"edmc.{_plugin_folder_name}")

_plugin_dir = None
_webhook_url = ""
_timeout_seconds = DEFAULT_TIMEOUT_SECONDS
_notify_jump_requests = True
_notify_jump_arrivals = True
_warned_missing_webhook = False

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

    if event == "CarrierJumpRequest" and _notify_jump_requests:
        _queue_discord_message(_format_jump_request(entry))
    elif event == "CarrierJump" and _notify_jump_arrivals:
        _queue_discord_message(_format_jump_arrival(entry))

    return None


def _load_config():
    global _webhook_url
    global _timeout_seconds
    global _notify_jump_requests
    global _notify_jump_arrivals
    global _warned_missing_webhook

    _webhook_url = os.environ.get(ENV_WEBHOOK_URL, "").strip()
    _timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    _notify_jump_requests = True
    _notify_jump_arrivals = True
    _warned_missing_webhook = False

    config_path = _config_path()
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not read %s", config_path)
            config = {}

        configured_webhook = str(config.get("discord_webhook_url", "")).strip()
        if configured_webhook:
            _webhook_url = configured_webhook

        _timeout_seconds = _positive_int(
            config.get("timeout_seconds"),
            DEFAULT_TIMEOUT_SECONDS,
        )
        _notify_jump_requests = bool(config.get("notify_jump_requests", True))
        _notify_jump_arrivals = bool(config.get("notify_jump_arrivals", True))

    if not _webhook_url:
        logger.warning(
            "%s has no Discord webhook. Set %s or add discord_webhook_url to %s.",
            PLUGIN_NAME,
            ENV_WEBHOOK_URL,
            config_path or CONFIG_FILENAME,
        )


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
            _send_discord_message(
                item["webhook_url"],
                item["content"],
                item["timeout_seconds"],
            )
        finally:
            _work_queue.task_done()


def _queue_discord_message(content):
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
            "content": content,
            "timeout_seconds": _timeout_seconds,
        }
    )


def _send_discord_message(webhook_url, content, timeout_seconds):
    payload = json.dumps({"content": content}).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
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


def _format_jump_request(entry):
    carrier = _carrier_name(entry)
    destination = entry.get("DestinationSystem") or "unknown destination"
    departure = entry.get("DepartureTime")

    lines = [
        f"{carrier} scheduled a carrier jump.",
        f"Destination: `{destination}`",
    ]
    if departure:
        lines.append(f"Departure: `{departure}`")

    return "\n".join(lines)


def _format_jump_arrival(entry):
    carrier = _carrier_name(entry)
    system = entry.get("StarSystem") or "unknown system"
    body = entry.get("Body")

    lines = [
        f"{carrier} completed a carrier jump.",
        f"Arrived: `{system}`",
    ]
    if body and body != system:
        lines.append(f"Body: `{body}`")

    return "\n".join(lines)


def _carrier_name(entry):
    return (
        entry.get("CarrierName")
        or entry.get("StationName")
        or entry.get("Callsign")
        or "Fleet carrier"
    )
