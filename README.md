# CQ Voice Keyer

A modern, open-source voice keyer for Amateur Radio (Ham Radio) operators. Designed to interface seamlessly with Hamlib (`rigctld`) for CAT rig control, and standard soundcards for high-quality audio routing. 

## Features
- **One-Click CQ:** Record your voice calling CQ, and play it back instantly with automatic PTT keying.
- **Auto-Repeat:** Loop your CQ sequence automatically with a customizable delay. 
- **Digital VFO Dial:** Hover and scroll your mouse wheel over the digits to instantly tune your radio.
- **Audio Monitoring:** Route your incoming radio audio to your PC headset with a built-in volume slider.
- **Fail-safe PTT Guard:** Automatically aborts transmitting if audio playback stalls or the radio disconnects.

---

## Setup & Rig Control (Hamlib `rigctld`)

This software relies on **Hamlib** (specifically `rigctld.exe`) to communicate with your radio. `rigctld` is a background service that translates network commands from CQ Voice Keyer into CAT commands for your specific radio model.

### 1. Installing Hamlib
1. Download the latest version of Hamlib for Windows (e.g. `hamlib-w64-4.5.5.zip`) from the [official Hamlib GitHub releases](https://github.com/Hamlib/Hamlib/releases).
2. Extract the ZIP file to a folder on your computer (e.g., `C:\Hamlib`).

### 2. Finding your Radio Model ID
Hamlib uses an ID number for each radio model. You can find your radio's ID by opening a Command Prompt and running:
```cmd
cd C:\Hamlib\bin
rigctl.exe -l
```
Scroll through the list to find your radio (e.g., the Yaesu FT-710 is usually `1047`).

### 3. Running `rigctld`
Before launching CQ Voice Keyer, you must start `rigctld.exe` so it can talk to your radio. Open a Command Prompt and run the following command, replacing the parameters with your radio's specifics:

```cmd
C:\Hamlib\bin\rigctld.exe -m 1047 -r COM4 -s 4800
```
- `-m 1047` is your Radio Model ID.
- `-r COM4` is the COM port your radio is connected to.
- `-s 4800` is the baud rate of your radio.

**Tip:** Create a `.bat` file on your desktop with this command so you can just double-click it to start your rig control before using the app!

### 4. Configuring CQ Voice Keyer
1. Launch CQ Voice Keyer.
2. Go to the **Settings** tab.
3. Under **Rig Settings**, ensure the COM port, baud rate, and radio model match what you used for `rigctld`.
4. Click **Test CAT** to confirm the connection is successful.

---

## Audio Setup

CQ Voice Keyer requires you to map your inputs and outputs correctly.

1. **Radio RX Input:** The soundcard input where your radio's receive audio comes in (e.g., Yaesu USB Audio).
2. **Radio TX Output:** The soundcard output that sends audio to your radio to transmit.
3. **Microphone Input:** Your PC Headset or desk microphone used to record your voice.
4. **Monitor Output:** Your PC Speakers or Headset used to monitor the radio traffic.

Make sure to adjust the **TX Audio Gain** slider on the Dashboard so you don't overdrive your radio's ALC!

## License
This project is open-source under the MIT License. See `LICENSE` for more details.
