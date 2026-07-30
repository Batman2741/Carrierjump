# EDMC Carrier Jump Plugin

this is a EDMarketConnector plugin for posting Elite Dangerous fleet carrier jump notifications to Discord.

## What it does

- Posts when a `CarrierJumpRequest` journal event schedules a carrier jump.
- Posts when a `CarrierJump` journal event confirms the carrier has arrived.
- Uses only Python standard library modules.
- Sends Discord webhook calls from a background thread so EDMC's UI is not blocked by network delays.

## Install

1. Put this folder in your EDMarketConnector plugins directory.
2. Make sure the folder contains `load.py`.
3. Restart EDMarketConnector.
4. Check EDMC Settings > Plugins and confirm `CarrierJump` is loaded.

## Configure

instructions for config
'''
replace the following values as needed:
discord_webhook_url
carrier_name
carrier_callsign
aside from that dont touch anything if you dont know what it is
for any problems please make a issue on github at https://github.com/Batman2741/Carrierjump/issues thank you
'''
```

You can also set the webhook with the `DISCORD_WEBHOOK_URL` environment variable. A value in `config.json` takes precedence over the environment variable.

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
- `CarrierJump` reports the arrival system as `StarSystem`; it does not reliably include `DestinationSystem`.
- For advance jump calls, this plugin uses `CarrierJumpRequest`.
- `CarrierJumpRequest` does not include the carrier's display name. The plugin learns the name from `CarrierStats` or `CarrierNameChanged`; set `carrier_name` and `carrier_callsign` in config if you want the correct name before those events appear.
