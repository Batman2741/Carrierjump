```python
import json
import logging
import requests

# Set up logging for your plugin
# You'll see these messages in EDMC's log window
LOGGER = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Replace this with the Webhook URL you copied from Discord!
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1528640289030541392/o7akgcvoXeOj5nFDT5RJd7G64gvgi35rGlMZBcWFJ7m6aWNDDiNNWGxh28dPrSy5xcvd"
# --- END CONFIGURATION ---

# This function is called by EDMC when a new journal entry is received
def journal_entry(cmdr, is_beta, system, station, entry, state):
    if entry["event"] == "CarrierJump":
        # Extract relevant information from the journal entry
        carrier_name = entry.get("CarrierName", "Unknown Carrier")
        current_system = entry.get("StarSystem", "Unknown System")
        destination_system = entry.get("DestinationSystem", "Unknown Destination")

        # Create the message for Discord
        message_content = (
            f"🚀 {carrier_name} is jumping!\n"
            f"From: `{current_system}`\n"
            f"To: `{destination_system}`"
        )

        # Prepare the data payload for the Discord webhook
        payload = {
            "content": message_content
        }

        try:
            # Send the message to Discord
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            LOGGER.info(f"Successfully sent Fleet Carrier jump notification to Discord for {carrier_name}.")
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Failed to send Discord notification: {e}")
        except Exception as e:
            LOGGER.error(f"An unexpected error occurred: {e}")

# This is an optional function, but good for debugging.
# It's called when EDMC loads your plugin.
def plugin_start(plugin_dir):
    LOGGER.info("FleetCarrierDiscord plugin started.")
    return "FleetCarrierDiscord" # Return the name of your plugin

# This is an optional function, called when EDMC stops your plugin.
def plugin_stop():
    LOGGER.info("FleetCarrierDiscord plugin stopped.")

# This is an optional function, called when EDMC reloads your plugin.
def plugin_reload():
    LOGGER.info("FleetCarrierDiscord plugin reloaded.")
```
