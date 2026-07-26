from load import journal_entry, plugin_reload, plugin_start3, plugin_stop


def plugin_start(plugin_dir):
    return plugin_start3(plugin_dir)
