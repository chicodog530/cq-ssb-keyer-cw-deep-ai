from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QFormLayout, QLineEdit, QHBoxLayout, QMessageBox, QGroupBox, QRadioButton, QGridLayout, QSpinBox, QSlider, QCheckBox
from PySide6.QtCore import Qt
import serial.tools.list_ports
from rig_control import RigController

class SettingsTab(QWidget):
    def __init__(self, audio_manager, settings_manager, rig_controller, parent=None):
        super().__init__(parent)
        self.audio_manager = audio_manager
        self.settings_manager = settings_manager
        self.rig_controller = rig_controller
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # General Settings
        self.show_tooltips_check = QCheckBox("Show Helpful Tooltips")
        self.show_tooltips_check.setChecked(self.settings_manager.get("show_tooltips", True))
        self.show_tooltips_check.stateChanged.connect(lambda s: self.settings_manager.set("show_tooltips", bool(s)))
        form_layout.addRow("UI:", self.show_tooltips_check)
        
        # Audio Settings
        self.rx_input_combo = QComboBox()
        self.tx_output_combo = QComboBox()
        self.mic_input_combo = QComboBox()
        self.monitor_output_combo = QComboBox()
        
        self.refresh_btn = QPushButton("Refresh Devices")
        self.refresh_btn.clicked.connect(self.populate_devices)
        
        form_layout.addRow("Radio RX Input:", self.rx_input_combo)
        form_layout.addRow("Radio TX Output:", self.tx_output_combo)
        form_layout.addRow("Microphone Input:", self.mic_input_combo)
        form_layout.addRow("Monitor Output:", self.monitor_output_combo)
        
        # Rig Settings
        self.rig_model_combo = QComboBox()
        self.populate_rig_models()
        
        self.rig_com_combo = QComboBox()
        self.populate_com_ports()
        
        self.rig_baud_combo = QComboBox()
        baud_rates = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
        self.rig_baud_combo.addItems(baud_rates)
        self.rig_baud_combo.setCurrentText(self.settings_manager.get("rig_baud", "4800"))
        
        self.rig_data_bits_combo = QComboBox()
        self.rig_data_bits_combo.addItems(["Default", "7", "8"])
        self.rig_data_bits_combo.setCurrentText(self.settings_manager.get("rig_data_bits", "Default"))
        
        self.rig_stop_bits_combo = QComboBox()
        self.rig_stop_bits_combo.addItems(["Default", "1", "2"])
        self.rig_stop_bits_combo.setCurrentText(self.settings_manager.get("rig_stop_bits", "Default"))
        
        self.rig_handshake_combo = QComboBox()
        self.rig_handshake_combo.addItems(["Default", "None", "XONXOFF", "Hardware"])
        self.rig_handshake_combo.setCurrentText(self.settings_manager.get("rig_handshake", "Default"))
        
        self.rig_dtr_combo = QComboBox()
        self.rig_dtr_combo.addItems(["Default", "High", "Low"])
        self.rig_dtr_combo.setCurrentText(self.settings_manager.get("rig_dtr", "Default"))
        
        self.rig_rts_combo = QComboBox()
        self.rig_rts_combo.addItems(["Default", "High", "Low"])
        self.rig_rts_combo.setCurrentText(self.settings_manager.get("rig_rts", "Default"))
        
        self.rig_model_combo.currentIndexChanged.connect(self.on_model_changed)
        self.rig_com_combo.currentTextChanged.connect(lambda t: self.settings_manager.set("rig_com_port", t.split(" ")[0] if t else ""))
        self.rig_baud_combo.currentTextChanged.connect(lambda t: self.settings_manager.set("rig_baud", t))
        self.rig_data_bits_combo.currentTextChanged.connect(lambda t: self.settings_manager.set("rig_data_bits", t))
        self.rig_stop_bits_combo.currentTextChanged.connect(lambda t: self.settings_manager.set("rig_stop_bits", t))
        self.rig_handshake_combo.currentTextChanged.connect(lambda t: self.settings_manager.set("rig_handshake", t))
        self.rig_dtr_combo.currentTextChanged.connect(lambda t: self.settings_manager.set("rig_dtr", t))
        self.rig_rts_combo.currentTextChanged.connect(lambda t: self.settings_manager.set("rig_rts", t))
        
        form_layout.addRow("Rigctld Model:", self.rig_model_combo)
        form_layout.addRow("Rigctld COM Port:", self.rig_com_combo)
        form_layout.addRow("Rigctld Baud Rate:", self.rig_baud_combo)
        form_layout.addRow("Data Bits:", self.rig_data_bits_combo)
        form_layout.addRow("Stop Bits:", self.rig_stop_bits_combo)
        form_layout.addRow("Handshake:", self.rig_handshake_combo)
        form_layout.addRow("DTR:", self.rig_dtr_combo)
        form_layout.addRow("RTS:", self.rig_rts_combo)
        
        # Rig Test Buttons
        rig_test_layout = QHBoxLayout()
        self.btn_test_cat = QPushButton("Test CAT")
        self.btn_test_ptt = QPushButton("Test PTT")
        
        self.btn_test_cat.clicked.connect(self.on_test_cat)
        self.btn_test_ptt.pressed.connect(lambda: self.rig_controller.set_ptt(True))
        self.btn_test_ptt.released.connect(lambda: self.rig_controller.set_ptt(False))
        
        rig_test_layout.addWidget(self.btn_test_cat)
        rig_test_layout.addWidget(self.btn_test_ptt)
        
        # PTT Method (Placeholder UI, hardcoded to CAT for now)
        ptt_group = QGroupBox("PTT Method")
        ptt_layout = QGridLayout(ptt_group)
        ptt_layout.addWidget(QRadioButton("VOX"), 0, 0)
        cat_btn = QRadioButton("CAT")
        cat_btn.setChecked(True)
        ptt_layout.addWidget(cat_btn, 1, 0)
        ptt_layout.addWidget(QRadioButton("DTR"), 0, 1)
        ptt_layout.addWidget(QRadioButton("RTS"), 1, 1)
        
        # Sequence Delays
        delay_group = QGroupBox("Sequence Delays")
        delay_layout = QGridLayout(delay_group)
        delay_layout.addWidget(QLabel("Pre-Roll (ms):"), 0, 0)
        self.pre_roll_spin = QSpinBox()
        self.pre_roll_spin.setRange(0, 5000)
        self.pre_roll_spin.setValue(self.settings_manager.get("tx_pre_roll_ms", 200))
        self.pre_roll_spin.valueChanged.connect(lambda v: self.settings_manager.set("tx_pre_roll_ms", v))
        delay_layout.addWidget(self.pre_roll_spin, 0, 1)
        
        delay_layout.addWidget(QLabel("Post-Roll (ms):"), 1, 0)
        self.post_roll_spin = QSpinBox()
        self.post_roll_spin.setRange(0, 5000)
        self.post_roll_spin.setValue(self.settings_manager.get("tx_post_roll_ms", 100))
        self.post_roll_spin.valueChanged.connect(lambda v: self.settings_manager.set("tx_post_roll_ms", v))
        delay_layout.addWidget(self.post_roll_spin, 1, 1)
        
        
        # External Services (QRZ, eQSL, LoTW)
        ext_group = QGroupBox("External Services & Auto-Logging")
        ext_layout = QFormLayout(ext_group)
        
        self.qrz_enable = QCheckBox("Enable QRZ Logbook Auto-Upload")
        self.qrz_enable.setChecked(self.settings_manager.get("qrz_enable", False))
        self.qrz_key = QLineEdit(self.settings_manager.get("qrz_api_key", ""))
        self.qrz_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.qrz_lookup_method = QComboBox()
        self.qrz_lookup_method.addItems(["Web Browser (Free)", "XML API Popup (Requires Paid Subscription)"])
        self.qrz_lookup_method.setCurrentText(self.settings_manager.get("qrz_lookup_method", "Web Browser (Free)"))
        
        self.eqsl_enable = QCheckBox("Enable eQSL Auto-Upload")
        self.eqsl_enable.setChecked(self.settings_manager.get("eqsl_enable", False))
        self.eqsl_user = QLineEdit(self.settings_manager.get("eqsl_user", ""))
        self.eqsl_pass = QLineEdit(self.settings_manager.get("eqsl_pass", ""))
        self.eqsl_pass.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        
        self.lotw_enable = QCheckBox("Enable LoTW Auto-Upload via TQSL")
        self.lotw_enable.setChecked(self.settings_manager.get("lotw_enable", False))
        self.lotw_path = QLineEdit(self.settings_manager.get("lotw_path", "C:\\Program Files (x86)\\TrustedQSL\\tqsl.exe"))
        
        ext_layout.addRow(self.qrz_enable)
        ext_layout.addRow("QRZ Lookup:", self.qrz_lookup_method)
        ext_layout.addRow("QRZ API Key:", self.qrz_key)
        
        ext_layout.addRow(self.eqsl_enable)
        ext_layout.addRow("eQSL User:", self.eqsl_user)
        ext_layout.addRow("eQSL Pass:", self.eqsl_pass)
        
        ext_layout.addRow(self.lotw_enable)
        ext_layout.addRow("TQSL.exe Path:", self.lotw_path)
        
        # Connect signals
        self.qrz_enable.stateChanged.connect(self.on_qrz_toggled)
        self.qrz_key.textChanged.connect(lambda t: self.settings_manager.set("qrz_api_key", t))
        self.qrz_lookup_method.currentTextChanged.connect(lambda t: self.settings_manager.set("qrz_lookup_method", t))
        
        self.eqsl_enable.stateChanged.connect(self.on_eqsl_toggled)
        self.eqsl_user.textChanged.connect(lambda t: self.settings_manager.set("eqsl_user", t))
        self.eqsl_pass.textChanged.connect(lambda t: self.settings_manager.set("eqsl_pass", t))
        
        self.lotw_enable.stateChanged.connect(self.on_lotw_toggled)
        self.lotw_path.textChanged.connect(lambda t: self.settings_manager.set("lotw_path", t))

        layout.addLayout(form_layout)
        layout.addWidget(self.refresh_btn)
        layout.addLayout(rig_test_layout)
        layout.addWidget(ptt_group)
        layout.addWidget(delay_group)
        layout.addWidget(ext_group)

        layout.addStretch()
        
        self.populate_devices()
        
        # Connect signals
        self.rx_input_combo.currentIndexChanged.connect(lambda idx: self.settings_manager.set("rx_input_index", self._get_device_index(self.audio_manager.get_input_devices(), idx)))
        self.tx_output_combo.currentIndexChanged.connect(lambda idx: self.settings_manager.set("tx_output_index", self._get_device_index(self.audio_manager.get_output_devices(), idx)))
        self.mic_input_combo.currentIndexChanged.connect(lambda idx: self.settings_manager.set("mic_input_index", self._get_device_index(self.audio_manager.get_input_devices(), idx)))
        self.monitor_output_combo.currentIndexChanged.connect(lambda idx: self.settings_manager.set("monitor_output_index", self._get_device_index(self.audio_manager.get_output_devices(), idx)))


    def on_qrz_toggled(self, state):
        self.settings_manager.set("qrz_enable", bool(state))
        if state:
            QMessageBox.information(self, "QRZ Logbook API", "QRZ Logbook auto-upload requires a paid XML Logbook Data subscription from QRZ.com.\n\nEnter your API key below.")
            
    def on_eqsl_toggled(self, state):
        self.settings_manager.set("eqsl_enable", bool(state))
        if state:
            QMessageBox.information(self, "eQSL API", "eQSL auto-upload will send your QSOs to eQSL.cc automatically.\n\nEnter your standard username and password below.")
            
    def on_lotw_toggled(self, state):
        self.settings_manager.set("lotw_enable", bool(state))
        if state:
            QMessageBox.information(self, "LoTW Uploads (TQSL)", "Logbook of the World requires the ARRL's TrustedQSL (tqsl) software to be installed on this PC.\n\nPlease verify the path to tqsl.exe below.")

    def populate_rig_models(self):
        models = RigController.get_models()
        self.rig_model_combo.clear()
        saved_model = self.settings_manager.get("rig_model", "1047")
        
        idx_to_select = 0
        self.model_data = [] # To map index back to model ID
        for i, (m_id, m_name) in enumerate(models):
            self.rig_model_combo.addItem(f"{m_id} - {m_name}")
            self.model_data.append(m_id)
            if m_id == saved_model:
                idx_to_select = i
                
        if self.rig_model_combo.count() > 0:
            self.rig_model_combo.setCurrentIndex(idx_to_select)

    def on_model_changed(self, idx):
        if 0 <= idx < len(self.model_data):
            self.settings_manager.set("rig_model", self.model_data[idx])

    def populate_com_ports(self):
        ports = serial.tools.list_ports.comports()
        self.rig_com_combo.clear()
        saved_port = self.settings_manager.get("rig_com_port", "")
        
        idx_to_select = 0
        for i, port in enumerate(ports):
            self.rig_com_combo.addItem(f"{port.device} - {port.description}")
            if port.device == saved_port:
                idx_to_select = i
                
        if self.rig_com_combo.count() > 0:
            self.rig_com_combo.setCurrentIndex(idx_to_select)
            
    def on_test_cat(self):
        if self.rig_controller.test_cat():
            QMessageBox.information(self, "CAT Test", "CAT Connection Successful!\nFreq: " + self.rig_controller.frequency)
        else:
            QMessageBox.critical(self, "CAT Test", f"CAT Connection Failed!\nEnsure Rigctld is running and configured correctly.\nError: {self.rig_controller.last_error}")
        
    def _get_device_index(self, devices, combo_idx):
        if 0 <= combo_idx < len(devices):
            return devices[combo_idx]['index']
        return None

    def _set_combo_index(self, combo, devices, saved_index):
        if saved_index is None:
            return
        for i, d in enumerate(devices):
            if d['index'] == saved_index:
                combo.setCurrentIndex(i)
                return

    def populate_devices(self):
        self.audio_manager.refresh_devices()
        
        in_devs = self.audio_manager.get_input_devices()
        out_devs = self.audio_manager.get_output_devices()
        
        inputs = [f"{d['index']}: {d['name']} ({d['hostapi']})" for d in in_devs]
        outputs = [f"{d['index']}: {d['name']} ({d['hostapi']})" for d in out_devs]
        
        # Block signals so we don't accidentally save blank settings when clearing
        self.rx_input_combo.blockSignals(True)
        self.mic_input_combo.blockSignals(True)
        self.tx_output_combo.blockSignals(True)
        self.monitor_output_combo.blockSignals(True)

        for combo in [self.rx_input_combo, self.mic_input_combo]:
            combo.clear()
            combo.addItems(inputs)
            
        for combo in [self.tx_output_combo, self.monitor_output_combo]:
            combo.clear()
            combo.addItems(outputs)
            
        self._set_combo_index(self.rx_input_combo, in_devs, self.settings_manager.get("rx_input_index"))
        self._set_combo_index(self.mic_input_combo, in_devs, self.settings_manager.get("mic_input_index"))
        self._set_combo_index(self.tx_output_combo, out_devs, self.settings_manager.get("tx_output_index"))
        self._set_combo_index(self.monitor_output_combo, out_devs, self.settings_manager.get("monitor_output_index"))
        
        self.rx_input_combo.blockSignals(False)
        self.mic_input_combo.blockSignals(False)
        self.tx_output_combo.blockSignals(False)
        self.monitor_output_combo.blockSignals(False)

