# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- **Live Mic (PTT) Feature**: Added a "Live Mic (PTT)" button to the dashboard that allows streaming audio directly from the PC microphone to the radio's TX output.
  - Automatically keys the radio's PTT while held down and unkeys when released.
  - Integrates with existing TX gain controls and limits output audio to prevent clipping (-1dBFS limit).
  - Displays microphone audio peaks on the TX Scope and audio meter.

### Fixed
- Fixed an issue where the application could crash on startup due to a missing `except` block in the audio engine monitoring code.

## [Initial Version] - 2026-08-09
### Added
- Initial project structure for the CQ Voice Keyer.
- Basic audio recording, monitoring, and TX routing functionality via PortAudio/sounddevice.
- Hamlib/rigctld TCP integration for basic frequency read/write and PTT control.
- Supervised CQ loop sequence state machine.
