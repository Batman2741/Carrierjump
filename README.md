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
  "notify_jump_requests": true,
  "notify_jump_arrivals": true,
  "timeout_seconds": 10
}
```

You can also set the webhook with the `ISSB_DISCORD_WEBHOOK_URL` environment variable. A value in `config.json` takes precedence over the environment variable.

## Notes

- Do not commit a real Discord webhook URL. If one has been committed or shared, rotate it in Discord.
- `CarrierJump` reports the arrival system as `StarSystem`; it does not reliably include `DestinationSystem`.
- For advance jump calls, this plugin uses `CarrierJumpRequest`.
