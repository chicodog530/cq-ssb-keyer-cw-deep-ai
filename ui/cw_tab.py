from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QCheckBox, QLabel, QSpinBox, QTextEdit, QLineEdit, QComboBox, QMenu, QInputDialog
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer
from ui.waterfall_widget import WaterfallWidget

class CWMacroButton(QPushButton):
    def __init__(self, index, text, cw_text, cw_tab_instance, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.cw_text = cw_text
        self.cw_tab = cw_tab_instance
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.clicked.connect(self.on_left_click)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        edit_text_action = QAction("Edit Button Text...", self)
        edit_text_action.triggered.connect(self.edit_text)
        menu.addAction(edit_text_action)
        
        edit_cw_action = QAction("Edit CW Macro Text...", self)
        edit_cw_action.triggered.connect(self.edit_cw_text)
        menu.addAction(edit_cw_action)
        
        menu.addSeparator()
        
        delete_action = QAction("Delete Preset", self)
        delete_action.triggered.connect(self.delete_preset)
        menu.addAction(delete_action)
        
        menu.exec_(self.mapToGlobal(pos))
        
    def edit_text(self):
        text, ok = QInputDialog.getText(self, "Edit Preset", "Button Text:", text=self.text())
        if ok and text:
            self.setText(text)
            self.cw_tab.save_macros()

    def edit_cw_text(self):
        text, ok = QInputDialog.getText(self, "Edit CW Text", "Enter the CW message to send:", text=self.cw_text)
        if ok:
            self.cw_text = text
            self.cw_tab.save_macros()
            
    def delete_preset(self):
        self.cw_tab.remove_macro(self)

    def on_left_click(self):
        self.cw_tab.cw_tx_input.setText(self.cw_text)

class CWTab(QWidget):
    def __init__(self, audio_engine, settings_manager, sequence_manager, cw_engine, parent=None):
        super().__init__(parent)
        self.audio_engine = audio_engine
        self.settings_manager = settings_manager
        self.sequence_manager = sequence_manager
        self.cw_engine = cw_engine
        
        layout = QVBoxLayout(self)
        
        # 1. Waterfall Group
        waterfall_group = QGroupBox("Audio Waterfall (Click to Tune)")
        waterfall_layout = QVBoxLayout()
        
        waterfall_controls = QHBoxLayout()
        waterfall_controls.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Classic", "Green Phosphor", "Monochrome"])
        self.theme_combo.currentTextChanged.connect(lambda t: self.waterfall.set_theme(t))
        waterfall_controls.addWidget(self.theme_combo)
        waterfall_controls.addStretch()
        waterfall_layout.addLayout(waterfall_controls)
        
        self.waterfall = WaterfallWidget()
        self.waterfall.frequencyClicked.connect(self.on_waterfall_clicked)
        waterfall_layout.addWidget(self.waterfall)
        waterfall_group.setLayout(waterfall_layout)
        layout.addWidget(waterfall_group)
        
        # 2. Decoder Group
        cw_group = QGroupBox("DeepCW AI Decoder")
        cw_layout = QVBoxLayout()
        self.cw_text_edit = QTextEdit()
        self.cw_text_edit.setReadOnly(True)
        self.cw_text_edit.setMinimumHeight(150)
        self.cw_text_edit.setStyleSheet("background-color: #000; color: #0f0; font-family: monospace; font-size: 16px;")
        
        cw_controls = QHBoxLayout()
        self.btn_cw_decode = QPushButton("Start CW AI Decode")
        self.btn_cw_decode.setStyleSheet("background-color: #004488; font-weight: bold; height: 30px;")
        self.btn_cw_decode.setCheckable(True)
        self.btn_cw_decode.toggled.connect(self.on_cw_decode_toggled)
        cw_controls.addWidget(self.btn_cw_decode)
        
        self.btn_cw_clear = QPushButton("Clear")
        self.btn_cw_clear.clicked.connect(self.cw_text_edit.clear)
        cw_controls.addWidget(self.btn_cw_clear)
        
        self.translate_check = QCheckBox("Expand Abbreviations")
        self.translate_check.setChecked(self.settings_manager.get("cw_translate", False))
        self.translate_check.stateChanged.connect(lambda s: self.settings_manager.set("cw_translate", bool(s)))
        cw_controls.addWidget(self.translate_check)
        cw_controls.addSpacing(10)
        
        # DSP Filter Controls
        self.cw_dsp_check = QCheckBox("DSP Bandpass")
        self.cw_dsp_check.setChecked(self.settings_manager.get("cw_dsp_enable", False))
        self.cw_dsp_check.stateChanged.connect(lambda s: self.settings_manager.set("cw_dsp_enable", bool(s)))
        cw_controls.addWidget(self.cw_dsp_check)
        
        cw_controls.addWidget(QLabel("Pitch:"))
        self.cw_dsp_pitch = QSpinBox()
        self.cw_dsp_pitch.setRange(300, 1500)
        self.cw_dsp_pitch.setValue(self.settings_manager.get("cw_dsp_pitch", 700))
        self.cw_dsp_pitch.setSingleStep(50)
        self.cw_dsp_pitch.valueChanged.connect(lambda v: self.settings_manager.set("cw_dsp_pitch", v))
        cw_controls.addWidget(self.cw_dsp_pitch)
        
        cw_controls.addWidget(QLabel("BW:"))
        self.cw_dsp_bw = QSpinBox()
        self.cw_dsp_bw.setRange(50, 500)
        self.cw_dsp_bw.setValue(self.settings_manager.get("cw_dsp_bw", 150))
        self.cw_dsp_bw.setSingleStep(50)
        self.cw_dsp_bw.valueChanged.connect(lambda v: self.settings_manager.set("cw_dsp_bw", v))
        cw_controls.addWidget(self.cw_dsp_bw)
        cw_controls.addStretch()
        
        self.wpm_label = QLabel("RX: -- WPM")
        self.wpm_label.setStyleSheet("color: #0f0; font-weight: bold; margin-right: 15px;")
        cw_controls.addWidget(self.wpm_label)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #aaa;")
        cw_controls.addWidget(self.status_label)
        
        cw_layout.addWidget(self.cw_text_edit)
        cw_layout.addLayout(cw_controls)
        cw_group.setLayout(cw_layout)
        layout.addWidget(cw_group)
        
        # 3. Encoder Group
        cw_tx_group = QGroupBox("CW Encoder (Send)")
        cw_tx_layout = QVBoxLayout()
        
        self.macro_layout = QHBoxLayout()
        self.macro_buttons = []
        self.load_macros()
        
        self.btn_add_macro = QPushButton("+ Add Preset")
        self.btn_add_macro.clicked.connect(self.add_macro)
        self.macro_layout.addWidget(self.btn_add_macro)
        self.macro_layout.addStretch()
        
        cw_tx_layout.addLayout(self.macro_layout)
        
        self.cw_tx_input = QLineEdit()
        self.cw_tx_input.setPlaceholderText("Type message to send in CW...")
        self.cw_tx_input.setStyleSheet("font-family: monospace; font-size: 16px;")
        
        cw_tx_controls = QHBoxLayout()
        cw_tx_controls.addWidget(QLabel("Speed (WPM):"))
        self.cw_wpm_spin = QSpinBox()
        self.cw_wpm_spin.setRange(5, 60)
        self.cw_wpm_spin.setValue(self.settings_manager.get("cw_wpm", 20))
        self.cw_wpm_spin.valueChanged.connect(lambda v: self.settings_manager.set("cw_wpm", v))
        cw_tx_controls.addWidget(self.cw_wpm_spin)
        
        cw_tx_controls.addWidget(QLabel("Pitch (Hz):"))
        self.cw_tx_pitch = QSpinBox()
        self.cw_tx_pitch.setRange(300, 1500)
        self.cw_tx_pitch.setValue(self.settings_manager.get("cw_pitch", 700))
        self.cw_tx_pitch.setSingleStep(50)
        self.cw_tx_pitch.valueChanged.connect(lambda v: self.settings_manager.set("cw_pitch", v))
        cw_tx_controls.addWidget(self.cw_tx_pitch)
        
        cw_tx_controls.addStretch()
        self.btn_send_cw = QPushButton("Send CW Audio")
        self.btn_send_cw.setStyleSheet("background-color: #660000; font-weight: bold; height: 30px;")
        self.btn_send_cw.clicked.connect(self.on_send_cw_clicked)
        cw_tx_controls.addWidget(self.btn_send_cw)
        
        cw_tx_layout.addWidget(self.cw_tx_input)
        cw_tx_layout.addLayout(cw_tx_controls)
        cw_tx_group.setLayout(cw_tx_layout)
        layout.addWidget(cw_tx_group)
        
        # Start timer for waterfall updates
        self.waterfall_timer = QTimer(self)
        self.waterfall_timer.timeout.connect(self.poll_waterfall)
        self.waterfall_timer.start(50)  # 20 FPS
        
        self.decode_buffer = ""
        self.translate_dict = {
            "QTH": "LOCATION", "QRM": "INTERFERENCE", "QRN": "STATIC",
            "QSO": "CONTACT", "73": "BEST REGARDS", "DE": "FROM",
            "ES": "AND", "PSE": "PLEASE", "TKS": "THANKS", "UR": "YOUR",
            "CQ": "CALLING ANY STATION", "K": "OVER", "SK": "END OF CONTACT",
            "TU": "THANK YOU", "OM": "OLD MAN", "XYL": "WIFE", "YL": "YOUNG LADY",
            "FB": "FINE BUSINESS", "HW": "HOW COPY?", "R": "ROGER",
            "WX": "WEATHER", "RIG": "RADIO", "ANT": "ANTENNA", "PWR": "POWER"
        }

    def load_macros(self):
        default_macros = [
            {"text": "CQ CQ CQ", "cw": "CQ CQ CQ"},
            {"text": "5NN TU", "cw": "5NN TU"},
            {"text": "73", "cw": "73"},
            {"text": "QRL?", "cw": "QRL?"},
            {"text": "QTH", "cw": "QTH"}
        ]
        macros_data = self.settings_manager.get("cw_presets", None)
        if macros_data is None:
            macros_data = default_macros
            
        for idx, m_data in enumerate(macros_data):
            btn = CWMacroButton(idx, m_data.get("text", f"Preset {idx+1}"), m_data.get("cw", ""), self)
            self.macro_layout.insertWidget(idx, btn)
            self.macro_buttons.append(btn)

    def reload_macros(self):
        for btn in self.macro_buttons:
            self.macro_layout.removeWidget(btn)
            btn.setParent(None)
            btn.deleteLater()
        self.macro_buttons.clear()
        self.load_macros()

    def add_macro(self):
        macros_data = self.settings_manager.get("cw_presets", [])
        if not macros_data:
            macros_data = [{"text": "CQ CQ CQ", "cw": "CQ CQ CQ"}] # just to have something if it was empty
        macros_data.append({"text": f"New Preset {len(macros_data)+1}", "cw": ""})
        self.settings_manager.set("cw_presets", macros_data)
        self.reload_macros()

    def remove_macro(self, btn):
        macros_data = self.settings_manager.get("cw_presets", [])
        if btn.index < len(macros_data):
            macros_data.pop(btn.index)
            self.settings_manager.set("cw_presets", macros_data)
            self.reload_macros()

    def save_macros(self):
        macros_data = []
        for btn in self.macro_buttons:
            macros_data.append({"text": btn.text(), "cw": btn.cw_text})
        self.settings_manager.set("cw_presets", macros_data)

    def on_waterfall_clicked(self, freq):
        self.cw_dsp_pitch.setValue(freq)
        self.cw_dsp_check.setChecked(True)
        self.status_label.setText(f"Tuned filter to {freq} Hz")
        
    def poll_waterfall(self):
        # Fetch latest audio buffer if available
        if hasattr(self.audio_engine, 'cw_raw_buffer') and len(self.audio_engine.cw_raw_buffer) > 0:
            if hasattr(self.audio_engine, 'cw_samplerate'):
                self.waterfall.update_waterfall(self.audio_engine.cw_raw_buffer, self.audio_engine.cw_samplerate)
                
        # Update overlay
        if self.btn_cw_decode.isChecked():
            if self.cw_dsp_check.isChecked():
                pitch = self.cw_dsp_pitch.value()
                bw = self.cw_dsp_bw.value()
                self.waterfall.set_overlay(True, pitch - bw/2, pitch + bw/2, True)
            else:
                self.waterfall.set_overlay(True, 400, 1200, False)
        else:
            self.waterfall.set_overlay(False)

    def on_cw_decode_toggled(self, checked):
        if not hasattr(self, 'cw_engine') or not self.cw_engine:
            self.status_label.setText("DeepCW engine not loaded. Check model files.")
            self.btn_cw_decode.setChecked(False)
            return
            
        if checked:
            rx_idx = self.settings_manager.get("rx_input_index")
            if rx_idx is None:
                self.status_label.setText("Error: Select RX Input in Settings first")
                self.btn_cw_decode.setChecked(False)
                return
            
            self.status_label.setText("Decoding...")
            def on_decode_text(text, wpm=None):
                from PySide6.QtCore import QMetaObject, Q_ARG, Qt
                
                if wpm is not None:
                    # Only update if we have a valid WPM
                    QMetaObject.invokeMethod(self.wpm_label, "setText", Qt.QueuedConnection, Q_ARG(str, f"RX: {wpm} WPM"))
                
                if not text:
                    return
                
                if self.translate_check.isChecked():
                    self.decode_buffer += text
                    parts = self.decode_buffer.split(" ")
                    if len(parts) > 1:
                        out_text = ""
                        for w in parts[:-1]:
                            w_clean = w.strip()
                            if w_clean in self.translate_dict:
                                out_text += f"{w_clean} [{self.translate_dict[w_clean]}] "
                            else:
                                out_text += f"{w} "
                        self.decode_buffer = parts[-1]
                        if out_text:
                            QMetaObject.invokeMethod(self.cw_text_edit, "insertPlainText", Qt.QueuedConnection, Q_ARG(str, out_text))
                else:
                    if self.decode_buffer:
                        QMetaObject.invokeMethod(self.cw_text_edit, "insertPlainText", Qt.QueuedConnection, Q_ARG(str, self.decode_buffer))
                        self.decode_buffer = ""
                    QMetaObject.invokeMethod(self.cw_text_edit, "insertPlainText", Qt.QueuedConnection, Q_ARG(str, text + " "))
                
            success = self.audio_engine.start_cw_decoding(
                rx_idx, 
                self.cw_engine, 
                on_decode_text,
                use_filter=self.cw_dsp_check.isChecked(),
                filter_freq=self.cw_dsp_pitch.value(),
                filter_bw=self.cw_dsp_bw.value()
            )
            if not success:
                self.btn_cw_decode.setChecked(False)
        else:
            self.audio_engine.stop_cw_decoding()
            self.status_label.setText("Stopped.")

    def on_send_cw_clicked(self):
        text = self.cw_tx_input.text().strip()
        if not text:
            self.status_label.setText("Please enter some text to send in CW.")
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
        temp_wav = os.path.join(tempfile.gettempdir(), "cw_tx_temp.wav")
        
        wpm = self.cw_wpm_spin.value()
        pitch = self.cw_tx_pitch.value()
        
        try:
            self.audio_engine.generate_cw_wav(text, temp_wav, wpm=wpm, freq_hz=pitch)
        except Exception as e:
            self.status_label.setText(f"Error generating CW: {e}")
            return
            
        if not os.path.exists(temp_wav):
            self.status_label.setText("Failed to generate CW audio file.")
            return
            
        self.sequence_manager.start_sequence(
            temp_wav,
            repeat_enabled=False,
            max_repeats=1,
            repeat_interval_ms=10000
        )
        self.cw_tx_input.clear()
