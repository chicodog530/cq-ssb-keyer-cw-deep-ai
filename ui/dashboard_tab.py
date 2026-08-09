from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar, QScrollArea, QMenu, QInputDialog, QFileDialog, QCheckBox, QLineEdit, QSpinBox, QDialog, QGroupBox, QSlider, QGridLayout, QToolButton, QWidgetAction, QComboBox
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QAction, QPainter, QColor, QPen, QShortcut, QKeySequence, QWheelEvent
import time
import os
import numpy as np
import datetime
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
import urllib.request
import xml.etree.ElementTree as ET
from external_loggers import ExternalLoggerUploader
from adif_logger import ADIFLogger

class FrequencyWidget(QWidget):
    valueChanged = Signal(int)
    
    def __init__(self, initial_hz=7074000, parent=None):
        super().__init__(parent)
        self.freq_hz = initial_hz
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(2)
        
        self.digit_labels = []
        for i in range(8):
            lbl = QLabel("0")
            lbl.setStyleSheet("background-color: #222; color: #0f0; font-size: 24px; font-family: monospace; padding: 2px; border-radius: 3px;")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setMinimumWidth(22)
            self.digit_labels.append(lbl)
            layout.addWidget(lbl)
            
            if i in [1, 4]:
                comma = QLabel(".")
                comma.setStyleSheet("color: #0f0; font-size: 24px; font-weight: bold;")
                layout.addWidget(comma)
                
        self.update_display()
        
    def update_display(self):
        s = f"{self.freq_hz:08d}"
        for i in range(8):
            self.digit_labels[i].setText(s[i])
            
    def wheelEvent(self, event: QWheelEvent):
        pos = event.position().toPoint()
        child = self.childAt(pos)
        if child in self.digit_labels:
            idx = self.digit_labels.index(child)
            power = 7 - idx
            delta = 10 ** power
            if event.angleDelta().y() > 0:
                self.freq_hz += delta
            else:
                self.freq_hz -= delta
            
            if self.freq_hz < 0: self.freq_hz = 0
            if self.freq_hz > 99999999: self.freq_hz = 99999999
            
            self.update_display()
            self.valueChanged.emit(self.freq_hz)

class QAudioScope(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.buffer = np.zeros(512, dtype=np.float32)
        
    def update_buffer(self, data):
        # Only update if visible to save CPU
        if self.isVisible():
            self.buffer = data.copy()
            self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 20, 30))
        
        pen = QPen(QColor(0, 255, 128))
        pen.setWidth(1)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        mid_y = h / 2
        
        if len(self.buffer) == 0:
            return
            
        step = w / len(self.buffer)
        for i in range(1, len(self.buffer)):
            x1 = int((i-1) * step)
            y1 = int(mid_y - (self.buffer[i-1] * mid_y))
            x2 = int(i * step)
            y2 = int(mid_y - (self.buffer[i] * mid_y))
            painter.drawLine(x1, y1, x2, y2)
            
    def mouseDoubleClickEvent(self, event):
        self.buffer.fill(0)
        self.update()

class PresetButton(QPushButton):
    def __init__(self, index, text, file, settings_manager, dashboard, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.audio_file = file
        self.settings_manager = settings_manager
        self.dashboard = dashboard
        
        self.setMinimumHeight(50)
        
        # Setup Context Menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.clicked.connect(self.on_left_click)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        edit_text_action = QAction("Edit Button Text...", self)
        edit_text_action.triggered.connect(self.edit_text)
        menu.addAction(edit_text_action)
        
        record_mic_action = QAction("Record from PC Mic...", self)
        record_mic_action.triggered.connect(self.record_from_mic)
        menu.addAction(record_mic_action)
        
        set_file_action = QAction("Select Existing Audio File...", self)
        set_file_action.triggered.connect(self.set_file)
        menu.addAction(set_file_action)
        
        norm_action = QAction("Normalize to -3dB", self)
        norm_action.triggered.connect(self.normalize_audio)
        menu.addAction(norm_action)
        
        preview_action = QAction("Preview on PC", self)
        preview_action.triggered.connect(self.preview_audio)
        menu.addAction(preview_action)
        
        menu.addSeparator()
        
        delete_action = QAction("Delete Preset", self)
        delete_action.triggered.connect(self.delete_preset)
        menu.addAction(delete_action)
        
        menu.exec_(self.mapToGlobal(pos))
        
    def delete_preset(self):
        self.dashboard.remove_preset(self)

    def normalize_audio(self):
        if not self.audio_file or not os.path.exists(self.audio_file):
            self.dashboard.status_label.setText("No audio file set for this preset.")
            return
            
        try:
            import soundfile as sf
            import numpy as np
            data, fs = sf.read(self.audio_file, dtype='float32')
            if len(data) > 0:
                peak = np.max(np.abs(data))
                if peak > 0:
                    target_peak = 10 ** (-3.0 / 20.0)
                    data = data * (target_peak / peak)
                    sf.write(self.audio_file, data, fs)
                    self.dashboard.status_label.setText(f"Normalized {self.text()} to -3dB")
        except Exception as e:
            self.dashboard.status_label.setText(f"Error normalizing: {e}")

    def edit_text(self):
        text, ok = QInputDialog.getText(self, "Edit Preset", "Button Text:", text=self.text())
        if ok and text:
            self.setText(text)
            self.dashboard.save_presets()

    def set_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.wav)")
        if file:
            self.audio_file = file
            self.dashboard.save_presets()

    def record_from_mic(self):
        mic_idx = self.settings_manager.get("mic_input_index")
        if mic_idx is None:
            self.dashboard.status_label.setText("Error: Select Microphone Input in Settings first")
            return
            
        if not self.dashboard.audio_engine.is_device_valid(mic_idx, 'input'):
            self.dashboard.status_label.setText("Error: Microphone unplugged or invalid!")
            return
            
        recordings_dir = os.path.abspath(self.settings_manager.get("recordings_dir", "recordings"))
        os.makedirs(recordings_dir, exist_ok=True)
        
        # Propose a default name based on the button's text (strip invalid Windows characters)
        import re
        clean_text = re.sub(r'[\\/*?:"<>|]', '', self.text())
        default_name = clean_text.replace(' ', '_') + ".wav"
        default_path = os.path.join(recordings_dir, default_name)
        
        file, _ = QFileDialog.getSaveFileName(self, "Save Recording As", default_path, "Audio Files (*.wav)")
        if not file:
            return
            
        final_filename = file
        temp_filename = final_filename + ".tmp"
        
        if self.dashboard.audio_engine.start_recording(mic_idx, temp_filename):
            dialog = QDialog(self)
            dialog.setWindowTitle("Recording Preset")
            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel("Recording from PC Microphone..."))
            stop_btn = QPushButton("Stop Recording")
            layout.addWidget(stop_btn)
            
            def stop_and_save():
                self.dashboard.audio_engine.stop_recording()
                
                # Atomic replace
                if os.path.exists(temp_filename):
                    if os.path.exists(final_filename):
                        try:
                            os.remove(final_filename)
                        except OSError:
                            pass
                    try:
                        os.rename(temp_filename, final_filename)
                        self.audio_file = os.path.abspath(final_filename)
                        self.dashboard.save_presets()
                    except OSError as e:
                        self.dashboard.status_label.setText(f"Error saving preset: {e}")
                        
                dialog.accept()
                
            stop_btn.clicked.connect(stop_and_save)
            dialog.exec_()
        else:
            self.dashboard.status_label.setText("Error starting microphone recording")

    def preview_audio(self):
        if not self.audio_file or not os.path.exists(self.audio_file):
            self.dashboard.status_label.setText("No audio file set for this preset.")
            return
            
        monitor_idx = self.settings_manager.get("monitor_output_index")
        if monitor_idx is None:
            self.dashboard.status_label.setText("Error: Select Monitor Output in Settings first")
            return
            
        if not self.dashboard.audio_engine.is_device_valid(monitor_idx, 'output'):
            self.dashboard.status_label.setText("Error: Monitor device unplugged or invalid!")
            return
            
        if self.dashboard.audio_engine.start_playback(monitor_idx, self.audio_file, self.settings_manager.get("tx_gain_db", -6)):
            self.dashboard.status_label.setText(f"Previewing: {self.text()}")

    def on_left_click(self):
        if not self.audio_file or not os.path.exists(self.audio_file):
            self.dashboard.status_label.setText("No audio file set for this preset.")
            return
            
        tx_idx = self.settings_manager.get("tx_output_index")
        if tx_idx is None:
            self.dashboard.status_label.setText("Error: Select TX Output in Settings first")
            return
            
        if not self.dashboard.audio_engine.is_device_valid(tx_idx, 'output'):
            self.dashboard.status_label.setText("Error: TX output device unplugged or invalid!")
            return
            
        # Key the radio and play the sequence via State Machine
        self.dashboard.sequence_manager.start_sequence(
            self.audio_file,
            repeat_enabled=self.dashboard.repeat_checkbox.isChecked(),
            max_repeats=self.dashboard.repeat_spinbox.value(),
            repeat_interval_ms=10000
        )

class DashboardTab(QWidget):
    def __init__(self, audio_engine, settings_manager, rig_controller, sequence_manager, parent=None):
        super().__init__(parent)
        self.audio_engine = audio_engine
        self.settings_manager = settings_manager
        self.rig_controller = rig_controller
        self.sequence_manager = sequence_manager
        
        # Connect Sequence Manager Signals
        self.sequence_manager.state_changed.connect(self.on_sequence_state_changed)
        
        self.last_recording = None
        self.adif_logger = ADIFLogger()
        self.external_uploader = ExternalLoggerUploader(self.settings_manager, self.adif_logger)
        self.external_uploader.upload_status.connect(self.on_upload_status)
        
        layout = QVBoxLayout(self)
        
        # Rig Status Panel
        rig_group = QGroupBox("Rig Status")
        rig_layout = QHBoxLayout()
        self.rig_conn_label = QLabel("Rig: Disconnected")
        self.rig_freq_label = QLabel("Freq: ---")
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.rig_mode_combo = QComboBox()
        self.rig_mode_combo.addItems(["LSB", "USB", "CW", "CWR", "AM", "FM", "PKTUSB", "PKTLSB", "RTTY", "RTTYR"])
        self.rig_mode_combo.currentTextChanged.connect(self.on_mode_combo_changed)
        mode_layout.addWidget(self.rig_mode_combo)
        
        self.rig_ptt_label = QLabel("PTT: OFF")
        
        self.freq_widget = FrequencyWidget()
        self.freq_timer = QTimer(self)
        self.freq_timer.setSingleShot(True)
        self.freq_timer.timeout.connect(self.on_freq_timer_expired)
        self.freq_widget.valueChanged.connect(lambda v: self.freq_timer.start(250))
        
        rig_layout.addWidget(self.rig_conn_label)
        rig_layout.addWidget(self.rig_freq_label)
        rig_layout.addLayout(mode_layout)
        rig_layout.addWidget(self.rig_ptt_label)
        rig_layout.addWidget(self.freq_widget)
        
        rig_group.setLayout(rig_layout)
        layout.addWidget(rig_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #33ff33;")
        
        # Scopes and Meters
        scopes_group = QGroupBox("Audio Scopes")
        scopes_layout = QHBoxLayout()
        
        rx_layout = QVBoxLayout()
        rx_layout.addWidget(QLabel("RX Audio (Mic/Radio)"))
        self.rx_scope = QAudioScope()
        rx_layout.addWidget(self.rx_scope)
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        rx_layout.addWidget(self.meter)
        
        tx_layout = QVBoxLayout()
        tx_layout.addWidget(QLabel("TX Audio (Playback)"))
        self.tx_scope = QAudioScope()
        tx_layout.addWidget(self.tx_scope)
        
        scopes_layout.addLayout(rx_layout)
        scopes_layout.addLayout(tx_layout)
        scopes_group.setLayout(scopes_layout)
        layout.addWidget(scopes_group)
        
        # Controls Group
        controls_group = QGroupBox("Manual Controls")
        controls_v_layout = QVBoxLayout()
        
        # Row 1: Audio and TX Controls
        controls_row1 = QHBoxLayout()
        self.monitor_checkbox = QCheckBox("Monitor RX on PC")
        self.monitor_checkbox.stateChanged.connect(self.on_monitor_changed)
        controls_row1.addWidget(self.monitor_checkbox)
        
        # Volume Drop Slider
        self.vol_btn = QToolButton()
        vol_val = self.settings_manager.get("monitor_volume", 100)
        self.vol_btn.setText(f"Vol: {vol_val}%")
        self.vol_btn.setPopupMode(QToolButton.InstantPopup)
        self.vol_btn.setStyleSheet("height: 25px; padding: 2px 10px;")
        vol_menu = QMenu(self)
        vol_action = QWidgetAction(self)
        vol_container = QWidget()
        vol_layout = QVBoxLayout(vol_container)
        self.monitor_vol_slider = QSlider(Qt.Horizontal)
        self.monitor_vol_slider.setRange(0, 100)
        self.monitor_vol_slider.setValue(vol_val)
        self.monitor_vol_slider.setMinimumWidth(150)
        self.monitor_vol_slider.valueChanged.connect(self.on_monitor_vol_changed)
        vol_layout.addWidget(QLabel("Monitor Volume:"))
        vol_layout.addWidget(self.monitor_vol_slider)
        vol_action.setDefaultWidget(vol_container)
        vol_menu.addAction(vol_action)
        self.vol_btn.setMenu(vol_menu)
        controls_row1.addWidget(self.vol_btn)
        
        # TX Gain Drop Slider
        self.tx_gain_btn = QToolButton()
        tx_val = self.settings_manager.get("tx_gain_db", -6)
        self.tx_gain_btn.setText(f"TX Gain: {tx_val}dB")
        self.tx_gain_btn.setPopupMode(QToolButton.InstantPopup)
        self.tx_gain_btn.setStyleSheet("height: 25px; padding: 2px 10px;")
        tx_menu = QMenu(self)
        tx_action = QWidgetAction(self)
        tx_container = QWidget()
        tx_layout = QVBoxLayout(tx_container)
        self.tx_gain_slider = QSlider(Qt.Horizontal)
        self.tx_gain_slider.setRange(-30, 0)
        self.tx_gain_slider.setValue(tx_val)
        self.tx_gain_slider.setMinimumWidth(150)
        self.tx_gain_slider.valueChanged.connect(self.on_tx_gain_changed)
        tx_layout.addWidget(QLabel("TX Audio Gain:"))
        tx_layout.addWidget(self.tx_gain_slider)
        tx_action.setDefaultWidget(tx_container)
        tx_menu.addAction(tx_action)
        self.tx_gain_btn.setMenu(tx_menu)
        controls_row1.addWidget(self.tx_gain_btn)
        
        self.btn_record = QPushButton("Record RX")
        self.btn_play = QPushButton("Quick Play RX")
        self.btn_test_tone = QPushButton("Test Tone (PTT)")
        self.btn_test_tone.setStyleSheet("background-color: #aa5500; font-weight: bold; height: 30px;")
        self.btn_live_mic = QPushButton("Live Mic (PTT)")
        self.btn_live_mic.setStyleSheet("background-color: #007700; font-weight: bold; height: 30px;")
        self.btn_stop = QPushButton("Stop All Audio / TX")
        self.btn_stop.setStyleSheet("background-color: #aa0000; font-weight: bold; height: 30px;")
        
        controls_row1.addWidget(self.btn_record)
        controls_row1.addWidget(self.btn_play)
        controls_row1.addWidget(self.btn_test_tone)
        controls_row1.addWidget(self.btn_live_mic)
        controls_row1.addWidget(self.btn_stop)
        
        # Row 2: Logging and Clock
        controls_row2 = QHBoxLayout()
        self.target_call_edit = QLineEdit()
        self.target_call_edit.setPlaceholderText("Target Callsign")
        self.target_call_edit.setMinimumWidth(150)
        self.target_call_edit.setStyleSheet("font-size: 14px; font-weight: bold; height: 28px;")
        
        self.btn_qrz = QPushButton("QRZ")
        self.btn_qrz.setStyleSheet("background-color: #000055; font-weight: bold; height: 30px;")
        
        self.btn_log = QPushButton("LOG")
        self.btn_log.setStyleSheet("background-color: #0000aa; font-weight: bold; height: 30px;")
        self.btn_log.setMinimumWidth(100)
        
        controls_row2.addWidget(self.target_call_edit)
        controls_row2.addWidget(self.btn_qrz)
        controls_row2.addWidget(self.btn_log)
        controls_row2.addStretch()
        
        self.utc_clock_label = QLabel("00:00:00 UTC")
        self.utc_clock_label.setStyleSheet("color: #0f0; font-size: 18px; font-family: monospace; font-weight: bold;")
        controls_row2.addWidget(self.utc_clock_label)
        
        # Row 3: TTS Exchange
        controls_row3 = QHBoxLayout()
        self.tts_checkbox = QCheckBox("TTS Voice Keyer")
        self.tts_checkbox.setChecked(False)
        
        self.tts_rst_edit = QLineEdit()
        self.tts_rst_edit.setPlaceholderText("RST (e.g. 59)")
        self.tts_rst_edit.setText("59")
        self.tts_rst_edit.setMaximumWidth(60)
        
        self.tts_custom_edit = QLineEdit()
        self.tts_custom_edit.setPlaceholderText("Custom Msg (Overrides Callsign)")
        self.tts_custom_edit.setMinimumWidth(150)
        
        self.btn_send_exchange = QPushButton("Send Exchange")
        self.btn_send_exchange.setStyleSheet("background-color: #660066; font-weight: bold; height: 30px;")
        self.btn_send_exchange.clicked.connect(self.on_send_exchange_clicked)
        
        controls_row3.addWidget(self.tts_checkbox)
        controls_row3.addWidget(self.tts_rst_edit)
        controls_row3.addWidget(self.tts_custom_edit)
        controls_row3.addWidget(self.btn_send_exchange)
        controls_row3.addStretch()
        
        controls_v_layout.addLayout(controls_row1)
        controls_v_layout.addLayout(controls_row2)
        controls_v_layout.addLayout(controls_row3)
        
        if self.settings_manager.get("show_tooltips", True):
            self.target_call_edit.setToolTip("Type the callsign of the station you are working here.\nWhen you click LOG, it will automatically fill in the log sheet.")
            self.btn_qrz.setToolTip("Look up this callsign on QRZ.com")
            self.btn_log.setToolTip("Open the ADIF Log Window to save this contact.")
            self.btn_live_mic.setToolTip("Press and hold to transmit audio directly from your PC Microphone.")
        
        self.btn_record.clicked.connect(self.on_record)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_play.clicked.connect(self.on_play)
        self.btn_test_tone.pressed.connect(self.on_test_tone_start)
        self.btn_test_tone.released.connect(self.on_test_tone_stop)
        self.btn_live_mic.pressed.connect(self.on_live_mic_start)
        self.btn_live_mic.released.connect(self.on_live_mic_stop)
        self.btn_qrz.clicked.connect(self.on_qrz_lookup)
        self.btn_log.clicked.connect(self.on_log_clicked)
        
        controls_group.setLayout(controls_v_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(controls_group)
        
        # Presets Section
        presets_group = QGroupBox("CQ Presets")
        presets_v_layout = QVBoxLayout()
        
        preset_header = QHBoxLayout()
        preset_header.addWidget(QLabel("CQ Presets (Left Click to TX, Right Click to Edit):"))
        preset_header.addStretch()
        self.repeat_checkbox = QCheckBox("Repeat Sequence")
        preset_header.addWidget(self.repeat_checkbox)
        preset_header.addWidget(QLabel("Max Repeats:"))
        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setRange(1, 20)
        self.repeat_spinbox.setValue(3)
        preset_header.addWidget(self.repeat_spinbox)
        
        preset_header.addSpacing(20)
        preset_header.addWidget(QLabel("Cols:"))
        self.preset_col_spinbox = QSpinBox()
        self.preset_col_spinbox.setRange(1, 8)
        self.preset_col_spinbox.setValue(self.settings_manager.get("preset_columns", 4))
        self.preset_col_spinbox.valueChanged.connect(self.on_preset_cols_changed)
        preset_header.addWidget(self.preset_col_spinbox)
        
        self.btn_add_preset = QPushButton("+ Add Preset")
        self.btn_add_preset.clicked.connect(self.add_preset)
        preset_header.addWidget(self.btn_add_preset)
        
        presets_v_layout.addLayout(preset_header)
        
        # Emergency Stop Shortcut
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.on_stop)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.presets_layout = QGridLayout(container)
        self.presets_layout.setAlignment(Qt.AlignTop)
        
        self.preset_buttons = []
        self.load_presets()
        
        scroll.setWidget(container)
        presets_v_layout.addWidget(scroll)
        presets_group.setLayout(presets_v_layout)
        layout.addWidget(presets_group)
        
        # Timer for meter and rig updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)  # 20 FPS

    def load_presets(self):
        default_presets = [
            {"text": "General CQ", "file": ""},
            {"text": "POTA CQ", "file": ""},
            {"text": "Station ID", "file": ""}
        ]
        presets_data = self.settings_manager.get("presets", None)
        if presets_data is None:
            presets_data = default_presets
        
        cols = self.settings_manager.get("preset_columns", 4)
        for idx, p_data in enumerate(presets_data):
            btn = PresetButton(idx, p_data.get("text", f"Preset {idx+1}"), p_data.get("file", ""), self.settings_manager, self)
            row = idx // cols
            col = idx % cols
            self.presets_layout.addWidget(btn, row, col)
            self.preset_buttons.append(btn)

    def reload_presets(self):
        for i in reversed(range(self.presets_layout.count())):
            widget = self.presets_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.preset_buttons.clear()
        self.load_presets()

    def on_preset_cols_changed(self, val):
        self.settings_manager.set("preset_columns", val)
        self.reload_presets()

    def add_preset(self):
        presets_data = self.settings_manager.get("presets", [])
        presets_data.append({"text": f"New Preset {len(presets_data)+1}", "file": ""})
        self.settings_manager.set("presets", presets_data)
        self.reload_presets()

    def remove_preset(self, btn):
        presets_data = self.settings_manager.get("presets", [])
        if btn.index < len(presets_data):
            presets_data.pop(btn.index)
            self.settings_manager.set("presets", presets_data)
            self.reload_presets()

    def save_presets(self):
        presets_data = []
        for btn in self.preset_buttons:
            presets_data.append({"text": btn.text(), "file": btn.audio_file})
        self.settings_manager.set("presets", presets_data)
        
    def on_monitor_vol_changed(self, val):
        self.settings_manager.set("monitor_volume", val)
        self.vol_btn.setText(f"Vol: {val}%")
        if self.audio_engine.is_monitoring:
            self.audio_engine.monitor_volume = val / 100.0

    def on_mode_combo_changed(self, mode):
        if self.rig_controller.connected:
            import threading
            threading.Thread(target=self.rig_controller.set_mode, args=(mode,), daemon=True).start()

    def on_tx_gain_changed(self, val):
        self.tx_gain_btn.setText(f"TX Gain: {val}dB")
        self.settings_manager.set("tx_gain_db", val)

    def on_monitor_changed(self, state):
        if state == 2: # Checked
            rx_idx = self.settings_manager.get("rx_input_index")
            mon_idx = self.settings_manager.get("monitor_output_index")
            if rx_idx is None or mon_idx is None:
                self.status_label.setText("Error: Setup RX and Monitor devices first.")
                self.monitor_checkbox.setChecked(False)
                return
            if not self.audio_engine.is_device_valid(rx_idx, 'input') or not self.audio_engine.is_device_valid(mon_idx, 'output'):
                self.status_label.setText("Error: RX or Monitor device unplugged or invalid!")
                self.monitor_checkbox.setChecked(False)
                return
            
            vol = self.settings_manager.get("monitor_volume", 100) / 100.0
            if not self.audio_engine.start_monitoring(rx_idx, mon_idx, volume=vol):
                self.monitor_checkbox.setChecked(False)
        else:
            self.audio_engine.stop_monitoring()
        
    def on_record(self):
        device_idx = self.settings_manager.get("rx_input_index")
        if device_idx is None:
            self.status_label.setText("Error: Select RX Input in Settings first")
            return
            
        if not self.audio_engine.is_device_valid(device_idx, 'input'):
            self.status_label.setText("Error: RX Input unplugged or invalid!")
            return
            
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(self.settings_manager.get("recordings_dir"), f"RX_{timestamp}.wav")
        self.last_recording = filename
        
        if self.audio_engine.start_recording(device_idx, filename):
            self.status_label.setText(f"Recording to {filename}...")
            self.btn_record.setEnabled(False)
        else:
            self.status_label.setText("Error starting recording")
            
    def on_sequence_state_changed(self, state, msg):
        if msg == "Transmitting Audio...":
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ff3333;")
        elif msg == "Ready":
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #33ff33;")
        else:
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #aaa;")
        self.status_label.setText(msg)

    def on_stop(self):
        self.sequence_manager.abort()
        self.audio_engine.stop_recording()
        self.audio_engine.stop_playback()
        if self.rig_controller.connected:
            self.rig_controller.set_ptt(False)
        self.status_label.setText("Stopped by User")
        self.btn_record.setEnabled(True)
        
    def on_send_exchange_clicked(self):
        if not self.tts_checkbox.isChecked():
            self.status_label.setText("Enable the 'TTS Voice Keyer' checkbox first.")
            return
            
        call = self.target_call_edit.text().strip()
        rst = self.tts_rst_edit.text().strip()
        custom = self.tts_custom_edit.text().strip()
        
        if not custom and not call:
            self.status_label.setText("No target callsign or custom message to speak.")
            return
            
        tx_idx = self.settings_manager.get("tx_output_index")
        if tx_idx is None:
            self.status_label.setText("Error: Select TX Output in Settings first")
            return
            
        if not self.audio_engine.is_device_valid(tx_idx, 'output'):
            self.status_label.setText("Error: TX output device unplugged or invalid!")
            return
            
        import tempfile
        import os
        temp_wav = os.path.join(tempfile.gettempdir(), "tts_exchange.wav")
        
        try:
            voice_id = self.settings_manager.get("tts_voice_id")
            rate = self.settings_manager.get("tts_rate", 150)
            self.audio_engine.generate_tts_wav(call, rst, temp_wav, custom_text=custom, voice_id=voice_id, rate=rate)
        except Exception as e:
            self.status_label.setText(f"Error generating TTS: {e}")
            return
            
        # Ensure file was generated
        if not os.path.exists(temp_wav):
            self.status_label.setText("Failed to generate TTS audio file.")
            return
            
        # Key the radio and play the sequence via State Machine
        self.sequence_manager.start_sequence(
            temp_wav,
            repeat_enabled=False,
            max_repeats=0,
            repeat_interval_ms=0
        )
        self.status_label.setText("Sending TTS Exchange...")

    def on_play(self):
        if not self.last_recording or not os.path.exists(self.last_recording):
            self.status_label.setText("No recent recording to play")
            return
            
        device_idx = self.settings_manager.get("monitor_output_index")
        if device_idx is None:
            self.status_label.setText("Error: Select Monitor Output in Settings first")
            return
            
        if not self.audio_engine.is_device_valid(device_idx, 'output'):
            self.status_label.setText("Error: Monitor output unplugged or invalid!")
            return
            
        if self.audio_engine.start_playback(device_idx, self.last_recording, self.settings_manager.get("tx_gain_db", -6)):
            self.status_label.setText(f"Playing {self.last_recording}...")
        else:
            self.status_label.setText("Error starting playback")

    def on_test_tone_start(self):
        tx_idx = self.settings_manager.get("tx_output_index")
        if tx_idx is None:
            self.status_label.setText("Error: Select TX Output in Settings first")
            return
            
        if not self.audio_engine.is_device_valid(tx_idx, 'output'):
            self.status_label.setText("Error: TX output device unplugged or invalid!")
            return
            
        if not self.rig_controller.connected:
            self.status_label.setText("Error: Rig disconnected")
            return
            
        if self.rig_controller.set_ptt(True):
            self.status_label.setText("Transmitting 1kHz Test Tone...")
            recordings_dir = self.settings_manager.get("recordings_dir", "recordings")
            os.makedirs(recordings_dir, exist_ok=True)
            tone_file = os.path.join(recordings_dir, "test_tone.wav")
            fs = 48000
            t = np.linspace(0, 10.0, int(fs*10.0), endpoint=False)
            tone = (np.sin(2 * np.pi * 1000 * t) * 0.95).astype(np.float32)
            import soundfile as sf
            sf.write(tone_file, tone, fs)
            
            tx_gain_db = self.settings_manager.get("tx_gain_db", -6)
            self.audio_engine.start_playback(tx_idx, tone_file, tx_gain_db)
            
    def on_test_tone_stop(self):
        self.audio_engine.stop_playback()
        if self.rig_controller.connected:
            self.rig_controller.set_ptt(False)
        self.status_label.setText("Stopped Test Tone")

    def on_live_mic_start(self):
        mic_idx = self.settings_manager.get("mic_input_index")
        tx_idx = self.settings_manager.get("tx_output_index")
        if mic_idx is None or tx_idx is None:
            self.status_label.setText("Error: Select Mic Input and TX Output in Settings")
            return
            
        if not self.audio_engine.is_device_valid(mic_idx, 'input') or not self.audio_engine.is_device_valid(tx_idx, 'output'):
            self.status_label.setText("Error: Devices unplugged or invalid!")
            return
            
        if not self.rig_controller.connected:
            self.status_label.setText("Error: Rig disconnected")
            return
            
        if self.rig_controller.set_ptt(True):
            self.status_label.setText("Live Mic: Transmitting...")
            tx_gain_db = self.settings_manager.get("tx_gain_db", -6)
            self.audio_engine.start_live_mic(mic_idx, tx_idx, tx_gain_db)
            
    def on_live_mic_stop(self):
        self.audio_engine.stop_live_mic()
        if self.rig_controller.connected:
            self.rig_controller.set_ptt(False)
        self.status_label.setText("Live Mic Stopped")

    def on_qrz_lookup(self):
        call = self.target_call_edit.text().strip()
        if not call:
            self.status_label.setText("Error: Enter a callsign to lookup")
            return
            
        method = self.settings_manager.get("qrz_lookup_method", "Web Browser (Free)")
        if "Browser" in method:
            QDesktopServices.openUrl(QUrl(f"https://www.qrz.com/db/{call}"))
        else:
            api_key = self.settings_manager.get("qrz_api_key", "")
            if not api_key:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "QRZ Error", "No QRZ API Key configured in Settings.")
                return
            
            # Simple async fetch to not block UI
            import threading
            def fetch_qrz():
                try:
                    url = f"http://xmldata.qrz.com/xml/current/?s={api_key};callsign={call}"
                    with urllib.request.urlopen(url, timeout=5) as response:
                        xml_data = response.read()
                        
                    root = ET.fromstring(xml_data)
                    # Use a crude parse for now
                    session = root.find("{http://xmldata.qrz.com}Session")
                    if session is not None and session.find("{http://xmldata.qrz.com}Error") is not None:
                        err = session.find("{http://xmldata.qrz.com}Error").text
                        self.status_label.setText(f"QRZ Error: {err}")
                        return
                        
                    callsign = root.find("{http://xmldata.qrz.com}Callsign")
                    if callsign is not None:
                        fname = callsign.findtext("{http://xmldata.qrz.com}fname", "")
                        name = callsign.findtext("{http://xmldata.qrz.com}name", "")
                        qth = callsign.findtext("{http://xmldata.qrz.com}qth", "")
                        state = callsign.findtext("{http://xmldata.qrz.com}state", "")
                        country = callsign.findtext("{http://xmldata.qrz.com}country", "")
                        
                        full_name = f"{fname} {name}".strip()
                        location = ", ".join(filter(None, [qth, state, country]))
                        
                        from PySide6.QtWidgets import QMessageBox
                        # This should technically be done via signals to the main thread, 
                        # but a quick QMessageBox in a worker thread usually works on Windows/PySide if careful.
                        # It's better to pass it to status for now to avoid cross-thread UI issues.
                        self.status_label.setText(f"QRZ: {call.upper()} - {full_name} ({location})")
                except Exception as e:
                    self.status_label.setText(f"QRZ Lookup Failed: {e}")
                    
            threading.Thread(target=fetch_qrz, daemon=True).start()

    def on_upload_status(self, service_name, status_msg):
        self.status_label.setText(f"{service_name}: {status_msg}")

    def on_log_clicked(self):
        # We will import LogWindow here to avoid circular imports if any, or just directly if available
        try:
            from ui.log_window import LogWindow
            target_call = self.target_call_edit.text().strip().upper()
            log_win = LogWindow(self.rig_controller, self.settings_manager, self.adif_logger, self.external_uploader, self)
            if target_call:
                log_win.call_edit.setText(target_call)
                self.target_call_edit.clear() # Clear it after opening log
            log_win.exec_()
        except Exception as e:
            self.status_label.setText(f"Error opening Log Window: {e}")

    def on_freq_timer_expired(self):
        freq_hz = self.freq_widget.freq_hz
        if self.rig_controller.connected:
            if self.rig_controller.set_frequency(freq_hz):
                self.status_label.setText(f"Set frequency to {freq_hz} Hz")
            else:
                self.status_label.setText("Failed to set frequency.")
        else:
            self.status_label.setText("Cannot set frequency: Rig disconnected.")

    def update_ui(self):
        # Update UTC Clock
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        self.utc_clock_label.setText(now_utc.strftime("%H:%M:%S UTC"))
        
        # Update Audio Scopes
        self.rx_scope.update_buffer(self.audio_engine.scope_data_rx)
        self.tx_scope.update_buffer(self.audio_engine.scope_data_tx)
        
        # Update Meter
        peak = self.audio_engine.current_peak
        self.meter.setValue(int(peak * 100))
        if self.audio_engine.is_clipping:
            self.meter.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif peak > 0.8:
            self.meter.setStyleSheet("QProgressBar::chunk { background-color: yellow; }")
        else:
            self.meter.setStyleSheet("QProgressBar::chunk { background-color: green; }")
            
        # Update Rig Status
        if self.rig_controller.connected:
            self.rig_conn_label.setText(f"Rig: Connected ({self.settings_manager.get('rig_model')})")
            self.rig_freq_label.setText(f"Freq: {self.rig_controller.frequency}")
            
            if self.rig_controller.mode and self.rig_controller.mode != self.rig_mode_combo.currentText():
                self.rig_mode_combo.blockSignals(True)
                if self.rig_mode_combo.findText(self.rig_controller.mode) == -1:
                    self.rig_mode_combo.addItem(self.rig_controller.mode)
                self.rig_mode_combo.setCurrentText(self.rig_controller.mode)
                self.rig_mode_combo.blockSignals(False)
            self.rig_ptt_label.setText(f"PTT: {'TX' if self.rig_controller.ptt_state else 'RX'}")
            if self.rig_controller.ptt_state:
                self.rig_ptt_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.rig_ptt_label.setStyleSheet("color: #aaa;")
                
            # Sync FrequencyWidget with Radio (if not currently scrolling/pending)
            try:
                rig_f = int(self.rig_controller.frequency)
                if not self.freq_timer.isActive() and self.freq_widget.freq_hz != rig_f:
                    self.freq_widget.freq_hz = rig_f
                    self.freq_widget.update_display()
            except:
                pass
                
        if not self.rig_controller.connected:
            self.rig_conn_label.setText("Rig: Disconnected")
            if self.rig_controller.last_error:
                self.rig_conn_label.setText(f"Rig Error: {self.rig_controller.last_error}")
            self.rig_freq_label.setText("Freq: ---")
            self.rig_ptt_label.setText("PTT: OFF")
            self.freq_widget.freq_hz = 0
            self.freq_widget.update_display()
            
            # Disable mode combo if disconnected
            if self.rig_mode_combo.isEnabled():
                self.rig_mode_combo.setEnabled(False)
        else:
            self.rig_conn_label.setText(f"Rig: Connected ({self.settings_manager.get('rig_model')})")
            
            if not self.rig_mode_combo.isEnabled():
                self.rig_mode_combo.setEnabled(True)
                
            if self.rig_controller.mode and self.rig_controller.mode != self.rig_mode_combo.currentText():
                self.rig_mode_combo.blockSignals(True)
                if self.rig_mode_combo.findText(self.rig_controller.mode) == -1:
                    self.rig_mode_combo.addItem(self.rig_controller.mode)
                self.rig_mode_combo.setCurrentText(self.rig_controller.mode)
                self.rig_mode_combo.blockSignals(False)
                
            self.rig_freq_label.setText(f"Freq: {self.rig_controller.frequency}")
            
            if self.rig_controller.ptt_state:
                self.rig_ptt_label.setText("PTT: TX")
                self.rig_ptt_label.setStyleSheet("color: #f00; font-weight: bold;")
            else:
                self.rig_ptt_label.setText("PTT: RX")
                self.rig_ptt_label.setStyleSheet("color: #888;")
