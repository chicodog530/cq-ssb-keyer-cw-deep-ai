import sounddevice as sd
import json

class AudioDeviceManager:
    def __init__(self):
        self.input_devices = []
        self.output_devices = []
        self.refresh_devices()

    def refresh_devices(self):
        devices = sd.query_devices()
        self.input_devices = []
        self.output_devices = []
        
        for i, dev in enumerate(devices):
            # Create a structured dict for each device
            device_info = {
                'index': i,
                'name': dev['name'],
                'hostapi': sd.query_hostapis(dev['hostapi'])['name'],
                'max_input_channels': dev['max_input_channels'],
                'max_output_channels': dev['max_output_channels'],
                'default_samplerate': dev['default_samplerate']
            }
            if dev['max_input_channels'] > 0:
                self.input_devices.append(device_info)
            if dev['max_output_channels'] > 0:
                self.output_devices.append(device_info)
                
    def get_input_devices(self):
        return self.input_devices
        
    def get_output_devices(self):
        return self.output_devices
