# core/plugin_manager.py
import os
import importlib.util
import inspect

class PluginManager:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = []

    def discover_plugins(self):
        """ Scans the plugins folder for python scripts """
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            return []

        found_plugins = []
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                plugin_name = filename[:-3] # remove .py
                plugin_path = os.path.join(self.plugin_dir, filename)
                
                try:
                    module = self.load_module(plugin_name, plugin_path)
                    if hasattr(module, "register_plugin"):
                        # We store the module and its metadata
                        info = module.register_plugin()
                        found_plugins.append({
                            "name": info.get("name", plugin_name),
                            "version": info.get("version", "1.0"),
                            "action": info.get("action"), # The function to call
                            "type": info.get("type", "tool") # tool, effect, exporter
                        })
                        print(f"✅ PLUGIN LOADED: {info.get('name')}")
                except Exception as e:
                    print(f"❌ PLUGIN ERROR ({filename}): {e}")
        
        self.plugins = found_plugins
        return self.plugins

    def load_module(self, name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod