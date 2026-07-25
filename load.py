```python
import sys
import os
import logging

# Set up logging for your plugin
# This will create a log file for plugin within the EDMC logs directory
plugin_name = "ISSB" 
logger = logging.getLogger(f"edmc.{plugin_name}")

# This function is called when EDMC loads your plugin
def plugin_start3(plugindir):
    """
    Starts the plugin.
    :param plugindir: The directory where your plugin is located.
    """
    logger.info(f"{plugin_name} starting up from {plugindir}")

    # --- Your plugin's initialization code goes here ---
    # For example, you might:
    # - Load configuration files
    # - Set up initial data structures
    # - Register event handlers (if your plugin reacts to game events)
    # - Initialize any external libraries your plugin uses

    logger.info(f"{plugin_name} successfully started.")
    return plugin_name # Return your plugin's name

# This function is called when EDMC is about to shut down
def plugin_stop():
    """
    Stops the plugin.
    """
    logger.info(f"{plugin_name} stopping.")
    # --- Your plugin's cleanup code goes here ---
    # For example, you might:
    # - Save any unsaved data
    # - Close open connections
    # - Perform final cleanup tasks
    logger.info(f"{plugin_name} stopped.")

# This function is called if your plugin needs to reload (e.g., after settings change)
def plugin_reload():
    """
    Reloads the plugin.
    """
    logger.info(f"{plugin_name} reloading.")
    # --- Your plugin's reload logic goes here ---
    # This might involve calling plugin_stop() then plugin_start3() again,
    # or just re-reading configuration.
    logger.info(f"{plugin_name} reloaded.")

# You can add other functions here that your plugin uses,
# for example, to handle events from Elite Dangerous.
# EDMC will call specific functions if they are defined, e.g.,
# journal_entry(cmdr, is_beta, system, station, entry, state)
# For now, we'll just keep the basic load/unload structure.

```
