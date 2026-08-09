# CQ Voice Keyer - User Manual

Welcome to CQ Voice Keyer, a universal radio audio recorder, voice keyer, and logger built for Ham Radio operators.

## Installation

1. Download and extract the application folder to your PC.
2. Double-click `installer.bat`. This will automatically create an isolated Python environment and install all necessary dependencies (PySide6, sounddevice, etc.).
3. Once the installer finishes, you can launch the app anytime by double-clicking `run.bat`.

## Initial Setup (Settings Tab)

Before operating, navigate to the **Settings** tab to configure your radio and audio routing.

### 1. Audio & Speech
- **Radio RX Input:** Select the virtual audio cable or soundcard bringing audio *from* your radio into your PC.
- **Radio TX Output:** Select the virtual audio cable or soundcard sending audio *to* your radio.
- **Microphone Input:** Select your physical PC microphone.
- **Monitor Output:** Select your PC speakers/headphones to hear playback.
- **TTS Voice & Speed:** Pick your preferred text-to-speech voice and adjust the words-per-minute (WPM) speed for automated exchanges.

### 2. Radio Control
- **Rigctld Configuration:** Ensure `rigctld` is running (the app attempts to bundle and run it for you). Select your Rig Model, COM Port, and Baud Rate. 
- **Test Controls:** Use the *Test CAT* and *Test PTT* buttons to verify your radio connects.

### 3. Logging & Services
- Enter your credentials for QRZ, eQSL, or LoTW if you want the app to automatically log your contacts to the cloud when you press the **LOG** button.

---

## Operating the Dashboard

The **Dashboard** tab is your main control surface during operation.

### Audio Scopes
Visualizes the audio coming from your radio (RX) and going to your radio (TX).

### Manual Controls
- **Monitor RX on PC:** Listen to your radio's RX audio through your PC speakers.
- **Vol & TX Gain:** Adjust your monitoring volume and the audio drive level going to your radio's TX.
- **Record RX:** Capture the last transmission you heard (useful for saving difficult callsigns).
- **Test Tone / Live Mic:** Instantly key the radio and broadcast a test tone or your PC microphone.
- **Stop All Audio / TX:** The panic button. Immediately stops any playback and unkeys the radio.

### Logging a Contact
1. Type the station's callsign in the **Target Callsign** box.
2. Click **QRZ** to quickly look up their details.
3. Click **LOG** to save the contact to your local ADIF file and upload it to your enabled cloud services.

### TTS Voice Keyer (Text-to-Speech)
To automate your exchanges:
1. Check the **TTS Voice Keyer** box.
2. Ensure you have a callsign typed in the *Target Callsign* box, and an RST (default is 59).
3. Click **Send Exchange**. The app will generate the phonetic callsign (e.g. "Kilo One Alpha, you are Five Nine"), key the radio, and transmit it.
4. *Custom Messages:* If you type in the "Custom Msg" box, clicking *Send Exchange* will speak exactly what you typed instead of the Callsign/RST.

### CQ Presets (Voice Keyer)
You can configure up to 8 automated audio sequences (like "CQ Contest" or your Station ID).
- **Right-Click a Preset:** Edit the button name and select an audio file (or record a new one using your mic).
- **Left-Click a Preset:** Instantly key the radio and play the audio file.
- **Repeat Sequence:** Check this box and set the max repeats to loop your CQ message automatically until you disable it.
