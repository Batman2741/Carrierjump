# ISSB EDMC Carrier Jump Plugin

ISSB is an EDMarketConnector plugin for posting Elite Dangerous fleet carrier jump notifications to Discord.

## What it does

- Posts when a `CarrierJumpRequest` journal event schedules a carrier jump.
- Posts when a `CarrierJump` journal event confirms the carrier has arrived.
- Uses only Python standard library modules.
- Sends Discord webhook calls from a background thread so EDMC's UI is not blocked by network delays.

## Install

1. Put this folder in your EDMarketConnector plugins directory.
2. Make sure the folder contains `load.py`.
3. Restart EDMarketConnector.
4. Check EDMC Settings > Plugins and confirm `ISSB` is loaded.

## Configure

Create a `config.json` file in the plugin folder:

```json
{
  "discord_webhook_url": "https://discord.com/api/webhooks/REPLACE_ME/REPLACE_ME",
  "carrier_name": "Spirula",
  "carrier_callsign": "L14-X1J",
  "notify_jump_requests": true,
  "notify_jump_arrivals": true,
  "timeout_seconds": 10,
  "embed": {
    "username": "ISSB Carrier Jumps",
    "avatar_url": "",
    "request": {
      "title": "{carrier} jump scheduled",
      "description": "",
      "color": "#3498DB",
      "fields": [
        {"name": "Carrier", "value": "{carrier}", "inline": true},
        {"name": "Destination", "value": "{destination}", "inline": true},
        {"name": "Body", "value": "{body}", "inline": true},
        {"name": "Departure", "value": "{departure_time}", "inline": false}
      ],
      "footer": "Elite Dangerous"
    },
    "arrival": {
      "title": "{carrier} arrived",
      "description": "",
      "color": "#57F287",
      "fields": [
        {"name": "Carrier", "value": "{carrier}", "inline": true},
        {"name": "System", "value": "{system}", "inline": true},
        {"name": "Body", "value": "{body}", "inline": true}
      ],
      "footer": "Elite Dangerous"
    }
  }
}
```

You can also set the webhook with the `ISSB_DISCORD_WEBHOOK_URL` environment variable. A value in `config.json` takes precedence over the environment variable.

The full example is available in `config.example.json`.

## Embed placeholders

Embed titles, descriptions, footers, and field values can use these placeholders:

- `{carrier}`: best available carrier display name.
- `{carrier_name}`: carrier name from `CarrierStats`, `CarrierNameChanged`, or `carrier_name`.
- `{carrier_callsign}`: carrier callsign from `CarrierStats`, `CarrierNameChanged`, or `carrier_callsign`.
- `{carrier_id}`: carrier market ID from `CarrierID` or `MarketID`.
- `{station_name}`: station name from arrival events.
- `{destination}`: requested jump destination.
- `{system}`: arrival system.
- `{body}`: requested or arrival body.
- `{body_id}`: body ID.
- `{departure_time}`: requested departure time.
- `{event}`: journal event name.
- `{timestamp}`: journal timestamp.

## Notes

- Do not commit a real Discord webhook URL. If one has been committed or shared, rotate it in Discord.
- `CarrierJump` reports the arrival system as `StarSystem`; it does not reliably include `DestinationSystem`.
- For advance jump calls, this plugin uses `CarrierJumpRequest`.
- `CarrierJumpRequest` does not include the carrier's display name. The plugin learns the name from `CarrierStats` or `CarrierNameChanged`; set `carrier_name` and `carrier_callsign` in config if you want the correct name before those events appear.
