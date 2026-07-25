import sys
import os
import logging

# Set up logging for  plugin
# This will create a log file for plugin within the EDMC logs directory
plugin_name = "ISSB" 
logger = logging.getLogger(f"edmc.{plugin_name}")

# This function is called when EDMC loads  plugin
def plugin_start3(plugindir):
    """
    Starts the plugin.
    :param plugindir: The directory where your plugin is located.
    """
    logger.info(f"{plugin_name} starting up from {plugindir}")

    logger.info(f"{plugin_name} successfully started.")
    return plugin_name # Return plugin's name

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

# This function is called if plugin needs to reload (e.g., after settings change)
def plugin_reload():
    """
    Reloads the plugin.
    """
    logger.info(f"{plugin_name} reloading.")
    logger.info(f"{plugin_name} reloaded.")
