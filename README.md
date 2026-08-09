# Universal Radio Audio Recorder & CQ Voice Keyer

A lightweight Windows desktop application designed for amateur radio operators to manage audio routing, record received signals, and automate CQ sequences using voice presets. The application interfaces with standard USB Audio Codecs and connects to Hamlib `rigctld` for CAT control (PTT and frequency monitoring).

## Features

- **CQ Sequence Automation**: Record your own voice presets (e.g., "CQ Contest") directly from your PC microphone.
- **Automated State Machine**: Handles PTT keying, pre-roll delays, audio playback, and post-roll unkeying safely.
- **Sequence Looping**: Loop your CQ sequences automatically with a customizable interval timer.
- **Audio Oscilloscopes**: Real-time visual feedback for both RX and TX audio streams.
- **Audio Routing**: Monitor the radio's audio on your PC speakers independently of the recording state.
- **CAT Control Integration**: Connects to `rigctld` (compatible with WSJT-X configurations) to handle PTT and frequency polling.

## Installation & Setup

### Prerequisites
1. Python 3.9+
2. `rigctld.exe` (Can be copied from a WSJT-X installation folder, usually `C:\WSJT\wsjtx\bin\rigctld-wsjtx.exe`)

### Dependencies
Install the required python packages:
```bash
pip install sounddevice soundfile numpy PySide6 pyserial
```

### Running the App
Double-click `run.bat` or run:
```bash
python main.py
```

## Configuration

1. **Audio Devices**: Go to the **Settings** tab and configure your input/output devices. For modern Windows setups, selecting the **WASAPI** version of your radio's USB Audio Codec is recommended. If WASAPI fails, select **MME**.
2. **Serial & CAT**: Configure your COM port and Baud rate in the Settings tab. Ensure these match your radio's settings and are identical to what you would use in WSJT-X.
3. **Sequence Delays**: Adjust the Pre-Roll (time between PTT and audio start) and Post-Roll (time after audio ends before dropping PTT) to accommodate your radio's physical relays (e.g., 200ms pre-roll, 100ms post-roll).

## Known Issues (For Jim)

### Low Audio Drive / TX Power (FT-710 and similar)
When transmitting a CQ sequence, the radio may only output a fraction of its maximum power (e.g., 7-8 watts on a 100W radio), even though the python application digitally normalizes the audio to maximum volume before playback.

**Troubleshooting Steps for Low Output:**
1. **Windows Volume Mixer**: The primary cause is usually Windows scaling down the volume of the Yaesu USB Audio Codec. Click the Windows speaker icon in the system tray, select the Yaesu output, and ensure it is pushed to 80-100%.
2. **Radio Mod Source**: Ensure the radio's **SSB MOD SOURCE** is set to `USB` or `REAR` instead of `MIC` (so it doesn't ignore the USB audio).
3. **USB Mod Level**: In the radio's menu, ensure the **USB MOD LEVEL** or **DATA IN LEVEL** is increased sufficiently to drive the ALC meter into the safe zone.
4. **Acoustic Coupling**: Verify that "TX Output" in the app's settings is *not* accidentally set to your PC desktop speakers. If it plays into the room, the physical radio mic might pick it up faintly, resulting in ~8 watts of output!
