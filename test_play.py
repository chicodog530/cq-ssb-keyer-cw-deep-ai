import sounddevice as sd
import numpy as np

try:
    print("Devices:")
    print(sd.query_devices())
except Exception as e:
    print(f"Error: {e}")
