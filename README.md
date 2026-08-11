# CQ Voice Keyer & DeepCW Decoder
**By KE0CGB**

A universal ham radio interface tool that allows you to easily manage Voice (SSB/AM/FM) and CW transmissions, record live audio, control your rig via CAT, and decode Morse Code in real-time using an AI Neural Network.

## Features
*   **DeepCW AI Decoder:** Uses a cutting-edge neural network (ONNX) to decode CW right off your receiver's audio passband.
*   **Audio CW Encoder:** Generate perfect Audio Modulated CW (MCW) tones to send CW via your digital audio interface (USB/LSB mode).
*   **Live Audio Waterfall:** Visually identify signals in your passband and simply click them to tune the DSP Bandpass filter!
*   **Voice Keyer:** Record presets, use Text-To-Speech (TTS), and chain audio files to send automated CQ calls.
*   **Rig Control:** Full integration with Hamlib's `rigctld` to read and set frequencies, modes, and PTT state.

## Installation
1. Go to the [Releases](https://github.com/chicodog530/cq-ssb-keyer-cw-deep-ai/releases) page and download `CQVoiceKeyer_Setup.exe`.
2. Run the installer and follow the instructions to install it on your PC.
3. The installer automatically bundles all dependencies, the AI models, and rig control binaries!

### Building from Source
If you want to modify the code or build the installer yourself:
1. Install Python 3.10+
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure you have the `rigctld` binaries in the `rigctld/` folder (included in standard releases).
4. Run `python main.py` to launch from source.

## Building the Windows Installer
You can build a standalone Windows Installer (`Setup.exe`) using PyInstaller and Inno Setup. 
1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php).
2. Simply double click the `build_exe.bat` file! 
3. It will automatically bundle the UI, Rig Control binaries, the AI `.onnx` models, and then invoke Inno Setup to create `CQVoiceKeyer_Setup.exe` in the `installer_out/` folder.

## License
MIT License. See `LICENSE` for more info.
