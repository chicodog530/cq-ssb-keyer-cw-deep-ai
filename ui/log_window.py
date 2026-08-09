from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
import datetime
import os
import sys

# Add parent directory to path to import adif_logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from adif_logger import ADIFLogger

def get_band_from_freq(freq_hz):
    # Simple band plan mapping
    if freq_hz is None: return ""
    mhz = freq_hz / 1000000.0
    if 1.8 <= mhz <= 2.0: return "160m"
    if 3.5 <= mhz <= 4.0: return "80m"
    if 5.3 <= mhz <= 5.4: return "60m"
    if 7.0 <= mhz <= 7.3: return "40m"
    if 10.1 <= mhz <= 10.15: return "30m"
    if 14.0 <= mhz <= 14.35: return "20m"
    if 18.068 <= mhz <= 18.168: return "17m"
    if 21.0 <= mhz <= 21.45: return "15m"
    if 24.89 <= mhz <= 24.99: return "12m"
    if 28.0 <= mhz <= 29.7: return "10m"
    if 50.0 <= mhz <= 54.0: return "6m"
    if 144.0 <= mhz <= 148.0: return "2m"
    if 420.0 <= mhz <= 450.0: return "70cm"
    return ""

class LogWindow(QDialog):
    def __init__(self, rig_controller, settings_manager, adif_logger=None, external_uploader=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log QSO")
        self.resize(400, 450)
        
        self.rig_controller = rig_controller
        self.settings_manager = settings_manager
        
        if adif_logger:
            self.logger = adif_logger
        else:
            self.logger = ADIFLogger()
            
        self.external_uploader = external_uploader
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.call_edit = QLineEdit()
        form_layout.addRow("Callsign:", self.call_edit)
        
        self.date_edit = QLineEdit()
        form_layout.addRow("Date (UTC):", self.date_edit)
        
        self.time_edit = QLineEdit()
        form_layout.addRow("Time (UTC):", self.time_edit)
        
        self.band_edit = QLineEdit()
        form_layout.addRow("Band:", self.band_edit)
        
        self.freq_edit = QLineEdit()
        form_layout.addRow("Frequency (MHz):", self.freq_edit)
        
        self.mode_edit = QLineEdit("SSB")
        form_layout.addRow("Mode:", self.mode_edit)
        
        self.rst_sent_edit = QLineEdit("59")
        form_layout.addRow("RST Sent:", self.rst_sent_edit)
        
        self.rst_rcvd_edit = QLineEdit("59")
        form_layout.addRow("RST Rcvd:", self.rst_rcvd_edit)
        
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)
        
        self.qth_edit = QLineEdit()
        form_layout.addRow("QTH:", self.qth_edit)
        
        self.comments_edit = QLineEdit()
        form_layout.addRow("Comments:", self.comments_edit)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save QSO")
        self.btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.btn_save.clicked.connect(self.save_qso)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.prefill_data()
        
    def prefill_data(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        self.date_edit.setText(now.strftime("%Y%m%d"))
        self.time_edit.setText(now.strftime("%H%M"))
        
        if self.rig_controller.connected:
            try:
                freq_hz = int(self.rig_controller.frequency)
            except (ValueError, TypeError):
                freq_hz = 0
                
            if freq_hz > 0:
                self.freq_edit.setText(f"{freq_hz / 1000000.0:.6f}")
                self.band_edit.setText(get_band_from_freq(freq_hz))
                
            mode = self.rig_controller.mode
            if mode:
                # Basic mapping, might need adjustment based on rig
                if "USB" in mode or "LSB" in mode:
                    self.mode_edit.setText("SSB")
                else:
                    self.mode_edit.setText(mode)

    def save_qso(self):
        if not self.call_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Callsign is required.")
            return
            
        qso_data = {
            "CALL": self.call_edit.text().strip().upper(),
            "DATE": self.date_edit.text().strip(),
            "TIME": self.time_edit.text().strip(),
            "BAND": self.band_edit.text().strip(),
            "FREQ": self.freq_edit.text().strip(),
            "MODE": self.mode_edit.text().strip().upper(),
            "RST_SENT": self.rst_sent_edit.text().strip(),
            "RST_RCVD": self.rst_rcvd_edit.text().strip(),
            "NAME": self.name_edit.text().strip(),
            "QTH": self.qth_edit.text().strip(),
            "COMMENTS": self.comments_edit.text().strip()
        }
        
        if self.logger.log_qso(qso_data):
            if self.external_uploader:
                self.external_uploader.upload_qso(qso_data)
            
            QMessageBox.information(self, "Success", "QSO logged successfully to local ADIF file.\nExternal uploads (if enabled) are running in the background.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to write QSO to log.")
