from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, QTextEdit, QLabel, QGroupBox
from PySide6.QtCore import Qt
from adif_logger import ADIFLogger

class LoggerTab(QWidget):
    def __init__(self, rig_controller, parent=None):
        super().__init__(parent)
        self.rig_controller = rig_controller
        self.logger = ADIFLogger()
        
        layout = QVBoxLayout(self)
        
        form_group = QGroupBox("Log New QSO")
        form_layout = QFormLayout()
        
        self.call_input = QLineEdit()
        self.rst_sent_input = QLineEdit("599")
        self.rst_rcvd_input = QLineEdit("599")
        self.name_input = QLineEdit()
        self.qth_input = QLineEdit()
        self.comments_input = QLineEdit()
        
        form_layout.addRow("Callsign:", self.call_input)
        form_layout.addRow("RST Sent:", self.rst_sent_input)
        form_layout.addRow("RST Rcvd:", self.rst_rcvd_input)
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("QTH:", self.qth_input)
        form_layout.addRow("Comments:", self.comments_input)
        
        btn_layout = QHBoxLayout()
        self.btn_log = QPushButton("Log QSO")
        self.btn_log.setStyleSheet("background-color: #006600; font-weight: bold; height: 30px;")
        self.btn_log.clicked.connect(self.log_qso)
        self.btn_clear = QPushButton("Clear Form")
        self.btn_clear.clicked.connect(self.clear_form)
        
        btn_layout.addWidget(self.btn_log)
        btn_layout.addWidget(self.btn_clear)
        form_layout.addRow("", btn_layout)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #aaa;")
        form_layout.addRow("", self.status_label)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Output / Recent
        recent_group = QGroupBox("Recent Logs (cq-voice-keyer-log.adi)")
        recent_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: monospace;")
        recent_layout.addWidget(self.log_text)
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        self.refresh_log_view()

    def clear_form(self):
        self.call_input.clear()
        self.rst_sent_input.setText("599")
        self.rst_rcvd_input.setText("599")
        self.name_input.clear()
        self.qth_input.clear()
        self.comments_input.clear()
        self.call_input.setFocus()
        
    def log_qso(self):
        call = self.call_input.text().strip()
        if not call:
            self.status_label.setText("Error: Callsign is required")
            return
            
        import datetime
        now = datetime.datetime.utcnow()
        
        freq = ""
        mode = ""
        if self.rig_controller.connected:
            if hasattr(self.rig_controller, 'frequency') and self.rig_controller.frequency and self.rig_controller.frequency != "Unknown":
                try:
                    # frequency is in Hz. ADIF expects MHz.
                    freq = f"{float(self.rig_controller.frequency) / 1000000.0:.6f}"
                except:
                    pass
            if hasattr(self.rig_controller, 'mode') and self.rig_controller.mode and self.rig_controller.mode != "Unknown":
                mode = self.rig_controller.mode
                
        if not mode:
            mode = "CW"
            
        qso_data = {
            "CALL": call,
            "DATE": now.strftime("%Y%m%d"),
            "TIME": now.strftime("%H%M%S"),
            "FREQ": freq,
            "MODE": mode,
            "RST_SENT": self.rst_sent_input.text().strip(),
            "RST_RCVD": self.rst_rcvd_input.text().strip(),
            "NAME": self.name_input.text().strip(),
            "QTH": self.qth_input.text().strip(),
            "COMMENTS": self.comments_input.text().strip()
        }
        
        success = self.logger.log_qso(qso_data)
        if success:
            self.status_label.setText(f"Logged QSO with {call} at {now.strftime('%H:%M:%S')} UTC")
            self.clear_form()
            self.refresh_log_view()
        else:
            self.status_label.setText(f"Failed to log QSO with {call}")

    def refresh_log_view(self):
        import os
        if os.path.exists(self.logger.filename):
            with open(self.logger.filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Show only last ~20 lines
                self.log_text.setText("".join(lines[-20:]))
                # scroll to bottom
                self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
