import json
import os

class SettingsManager:
    def __init__(self, filepath="settings.json"):
        self.filepath = filepath
        self.settings = {
            "rx_input_index": None,
            "tx_output_index": None,
            "mic_input_index": None,
            "monitor_output_index": None,
            "recordings_dir": "recordings"
        }
        self.load()
        
        if not os.path.exists(self.settings["recordings_dir"]):
            os.makedirs(self.settings["recordings_dir"])

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()
