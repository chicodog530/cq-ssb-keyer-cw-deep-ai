import os
import datetime

class ADIFLogger:
    def __init__(self, filename="cq-voice-keyer-log.adi"):
        app_data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'CQ Voice Keyer')
        if not os.path.exists(app_data_dir):
            try:
                os.makedirs(app_data_dir)
            except Exception:
                pass
        self.filename = os.path.join(app_data_dir, filename)
        self._ensure_header()

    def _ensure_header(self):
        if not os.path.exists(self.filename) or os.path.getsize(self.filename) == 0:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write("CQ Voice Keyer ADIF Log\n")
                f.write("<ADIF_VER:5>3.1.4\n")
                f.write("<PROGRAMID:14>CQ Voice Keyer\n")
                f.write("<EOH>\n\n")

    def _format_field(self, field_name, value):
        if not value:
            return ""
        value_str = str(value).strip()
        if not value_str:
            return ""
        return f"<{field_name.upper()}:{len(value_str)}>{value_str} "

    def log_qso(self, qso_data):
        """
        qso_data is a dict containing fields like:
        CALL, QSO_DATE, TIME_ON, BAND, FREQ, MODE, RST_SENT, RST_RCVD, NAME, QTH, COMMENT
        """
        record = ""
        
        # Standardize standard ADIF fields
        # Date should be YYYYMMDD
        # Time should be HHMM or HHMMSS
        # Freq should be in MHz (e.g. 7.074)
        
        # Map our friendly keys to exact ADIF keys
        adif_keys = {
            "CALL": "CALL",
            "DATE": "QSO_DATE",
            "TIME": "TIME_ON",
            "BAND": "BAND",
            "FREQ": "FREQ",
            "MODE": "MODE",
            "RST_SENT": "RST_SENT",
            "RST_RCVD": "RST_RCVD",
            "NAME": "NAME",
            "QTH": "QTH",
            "COMMENTS": "COMMENT"
        }
        
        for key, adif_key in adif_keys.items():
            if key in qso_data and qso_data[key]:
                record += self._format_field(adif_key, qso_data[key])
                
        if record:
            record += "<EOR>\n"
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(record)
            return True
        return False
