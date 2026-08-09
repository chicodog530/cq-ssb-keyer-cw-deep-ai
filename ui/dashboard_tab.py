from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar, QScrollArea, QMenu, QInputDialog, QFileDialog, QCheckBox, QLineEdit, QSpinBox, QDialog
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QPainter, QColor, QPen
import time
import os
import numpy as np

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
        
        preview_action = QAction("Preview on PC", self)
        preview_action.triggered.connect(self.preview_audio)
        menu.addAction(preview_action)
        
        menu.exec_(self.mapToGlobal(pos))

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
            
        recordings_dir = self.settings_manager.get("recordings_dir", "recordings")
        os.makedirs(recordings_dir, exist_ok=True)
        filename = os.path.join(recordings_dir, f"preset_{self.index}.wav")
        
        if self.dashboard.audio_engine.start_recording(mic_idx, filename):
            dialog = QDialog(self)
            dialog.setWindowTitle("Recording Preset")
            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel("Recording from PC Microphone..."))
            stop_btn = QPushButton("Stop Recording")
            layout.addWidget(stop_btn)
            
            def stop_and_save():
                self.dashboard.audio_engine.stop_recording()
                self.audio_file = os.path.abspath(filename)
                self.dashboard.save_presets()
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
            
        if self.dashboard.audio_engine.start_playback(monitor_idx, self.audio_file):
            self.dashboard.status_label.setText(f"Previewing: {self.text()}")

    def on_left_click(self):
        if not self.audio_file or not os.path.exists(self.audio_file):
            self.dashboard.status_label.setText("No audio file set for this preset.")
            return
            
        tx_idx = self.settings_manager.get("tx_output_index")
        if tx_idx is None:
            self.dashboard.status_label.setText("Error: Select TX Output in Settings first")
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
        
        layout = QVBoxLayout(self)
        
        # Rig Status Panel
        rig_layout = QHBoxLayout()
        self.rig_conn_label = QLabel("Rig: Disconnected")
        self.rig_freq_label = QLabel("Freq: ---")
        self.rig_mode_label = QLabel("Mode: ---")
        self.rig_ptt_label = QLabel("PTT: OFF")
        
        self.set_freq_edit = QLineEdit()
        self.set_freq_edit.setPlaceholderText("New Freq (Hz)")
        self.set_freq_btn = QPushButton("Set Freq")
        self.set_freq_btn.clicked.connect(self.on_set_freq)
        
        rig_layout.addWidget(self.rig_conn_label)
        rig_layout.addWidget(self.rig_freq_label)
        rig_layout.addWidget(self.rig_mode_label)
        rig_layout.addWidget(self.rig_ptt_label)
        rig_layout.addWidget(self.set_freq_edit)
        rig_layout.addWidget(self.set_freq_btn)
        
        layout.addLayout(rig_layout)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #aaa;")
        
        # Scopes and Meters
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
        
        # Checkbox
        self.monitor_checkbox = QCheckBox("Monitor RX on PC")
        self.monitor_checkbox.stateChanged.connect(self.on_monitor_changed)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.btn_record = QPushButton("Record RX")
        self.btn_stop = QPushButton("Stop All Audio / TX")
        self.btn_stop.setStyleSheet("background-color: #aa0000; font-weight: bold; height: 30px;")
        self.btn_play = QPushButton("Quick Play RX")
        
        controls_layout.addWidget(self.btn_record)
        controls_layout.addWidget(self.btn_stop)
        controls_layout.addWidget(self.btn_play)
        
        self.btn_record.clicked.connect(self.on_record)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_play.clicked.connect(self.on_play)
        
        layout.addWidget(self.status_label)
        layout.addLayout(scopes_layout)
        layout.addWidget(self.monitor_checkbox)
        layout.addLayout(controls_layout)
        
        # Presets Section
        preset_header = QHBoxLayout()
        preset_header.addWidget(QLabel("CQ Presets (Left Click to TX, Right Click to Edit):"))
        preset_header.addStretch()
        self.repeat_checkbox = QCheckBox("Repeat Sequence")
        preset_header.addWidget(self.repeat_checkbox)
        preset_header.addWidget(QLabel("Max Repeats (0=Inf):"))
        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setRange(0, 100)
        self.repeat_spinbox.setValue(3)
        preset_header.addWidget(self.repeat_spinbox)
        layout.addLayout(preset_header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.presets_layout = QVBoxLayout(container)
        self.presets_layout.setAlignment(Qt.AlignTop)
        
        self.preset_buttons = []
        self.load_presets()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
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
        presets_data = self.settings_manager.get("presets", default_presets)
        
        for idx, p_data in enumerate(presets_data):
            btn = PresetButton(idx, p_data.get("text", f"Preset {idx+1}"), p_data.get("file", ""), self.settings_manager, self)
            self.presets_layout.addWidget(btn)
            self.preset_buttons.append(btn)

    def save_presets(self):
        presets_data = []
        for btn in self.preset_buttons:
            presets_data.append({"text": btn.text(), "file": btn.audio_file})
        self.settings_manager.set("presets", presets_data)
        
    def on_monitor_changed(self, state):
        if state == 2: # Checked
            rx_idx = self.settings_manager.get("rx_input_index")
            mon_idx = self.settings_manager.get("monitor_output_index")
            if rx_idx is None or mon_idx is None:
                self.status_label.setText("Error: Setup RX and Monitor devices first.")
                self.monitor_checkbox.setChecked(False)
                return
            if not self.audio_engine.start_monitoring(rx_idx, mon_idx):
                self.monitor_checkbox.setChecked(False)
        else:
            self.audio_engine.stop_monitoring()
        
    def on_record(self):
        device_idx = self.settings_manager.get("rx_input_index")
        if device_idx is None:
            self.status_label.setText("Error: Select RX Input in Settings first")
            return
            
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(self.settings_manager.get("recordings_dir"), f"RX_{timestamp}.wav")
        self.last_recording = filename
        
        if self.audio_engine.start_recording(device_idx, filename):
            self.status_label.setText(f"Recording to {filename}...")
            self.btn_record.setEnabled(False)
        else:
            self.status_label.setText("Error starting recording")
            
    def on_sequence_state_changed(self, state, message):
        self.status_label.setText(f"Sequence: {message}")

    def on_stop(self):
        self.sequence_manager.abort()
        self.audio_engine.stop_recording()
        self.audio_engine.stop_playback()
        if self.rig_controller.connected:
            self.rig_controller.set_ptt(False)
        self.status_label.setText("Stopped by User")
        self.btn_record.setEnabled(True)
        
    def on_play(self):
        if not self.last_recording or not os.path.exists(self.last_recording):
            self.status_label.setText("No recent recording to play")
            return
            
        device_idx = self.settings_manager.get("monitor_output_index")
        if device_idx is None:
            self.status_label.setText("Error: Select Monitor Output in Settings first")
            return
            
        if self.audio_engine.start_playback(device_idx, self.last_recording):
            self.status_label.setText(f"Playing {self.last_recording}...")
        else:
            self.status_label.setText("Error starting playback")

    def on_set_freq(self):
        freq_text = self.set_freq_edit.text()
        try:
            freq_hz = int(freq_text)
            if self.rig_controller.connected:
                if self.rig_controller.set_frequency(freq_hz):
                    self.status_label.setText(f"Set frequency to {freq_hz} Hz")
                else:
                    self.status_label.setText("Failed to set frequency.")
            else:
                self.status_label.setText("Cannot set frequency: Rig disconnected.")
        except ValueError:
            self.status_label.setText("Invalid frequency value. Enter Hz.")

    def update_ui(self):
        if self.audio_engine.is_recording or self.audio_engine.is_monitoring:
            val = int(min(self.audio_engine.current_peak * 100, 100))
            self.meter.setValue(val)
        else:
            self.meter.setValue(0)
            
        # Update Scopes
        self.rx_scope.update_buffer(self.audio_engine.scope_data_rx)
        self.tx_scope.update_buffer(self.audio_engine.scope_data_tx)
            
        # Rig UI
        if self.rig_controller.connected:
            self.rig_conn_label.setText("Rig: Connected")
            self.rig_conn_label.setStyleSheet("color: green;")
            self.rig_freq_label.setText(f"Freq: {self.rig_controller.frequency}")
            self.rig_mode_label.setText(f"Mode: {self.rig_controller.mode}")
            self.rig_ptt_label.setText(f"PTT: {'ON' if self.rig_controller.ptt_state else 'OFF'}")
            self.rig_ptt_label.setStyleSheet("color: red;" if self.rig_controller.ptt_state else "")
        else:
            self.rig_conn_label.setText("Rig: Disconnected")
            self.rig_conn_label.setStyleSheet("color: red;")
            self.rig_freq_label.setText("Freq: ---")
            self.rig_mode_label.setText("Mode: ---")
            self.rig_ptt_label.setText("PTT: OFF")


