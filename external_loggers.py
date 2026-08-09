from PySide6.QtCore import QObject, Signal
import urllib.request
import urllib.parse
import subprocess
import os
import threading

class ExternalLoggerUploader(QObject):
    upload_status = Signal(str, str) # Service Name, Status Message
    
    def __init__(self, settings_manager, adif_logger_instance):
        super().__init__()
        self.settings = settings_manager
        self.adif_logger = adif_logger_instance
        
    def _format_adif_record(self, qso_data):
        # We can borrow the format logic from the local logger
        record = ""
        adif_keys = {
            "CALL": "CALL", "DATE": "QSO_DATE", "TIME": "TIME_ON", 
            "BAND": "BAND", "FREQ": "FREQ", "MODE": "MODE", 
            "RST_SENT": "RST_SENT", "RST_RCVD": "RST_RCVD", 
            "NAME": "NAME", "QTH": "QTH", "COMMENTS": "COMMENT"
        }
        for key, adif_key in adif_keys.items():
            if key in qso_data and qso_data[key]:
                val = str(qso_data[key]).strip()
                record += f"<{adif_key}:{len(val)}>{val} "
        if record:
            record += "<EOR>"
        return record

    def upload_qso(self, qso_data):
        adif_record = self._format_adif_record(qso_data)
        
        if self.settings.get("qrz_enable", False):
            threading.Thread(target=self._upload_qrz, args=(adif_record,), daemon=True).start()
            
        if self.settings.get("eqsl_enable", False):
            threading.Thread(target=self._upload_eqsl, args=(qso_data,), daemon=True).start()
            
        if self.settings.get("lotw_enable", False):
            threading.Thread(target=self._upload_lotw, args=(self.adif_logger.filename,), daemon=True).start()

    def _upload_qrz(self, adif_record):
        api_key = self.settings.get("qrz_api_key", "")
        if not api_key:
            self.upload_status.emit("QRZ", "Failed: No API Key")
            return
            
        try:
            data = urllib.parse.urlencode({
                'KEY': api_key,
                'ACTION': 'INSERT',
                'ADIF': adif_record
            }).encode('utf-8')
            
            req = urllib.request.Request("http://logbook.qrz.com/api", data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                result = response.read().decode('utf-8')
                if "RESULT=OK" in result:
                    self.upload_status.emit("QRZ", "Success")
                else:
                    # Try to extract reason
                    err = result.split("REASON=")[-1].split("&")[0] if "REASON=" in result else "Unknown Error"
                    self.upload_status.emit("QRZ", f"Error: {err}")
        except Exception as e:
            self.upload_status.emit("QRZ", f"Exception: {e}")

    def _upload_eqsl(self, qso_data):
        user = self.settings.get("eqsl_user", "")
        pwd = self.settings.get("eqsl_pass", "")
        if not user or not pwd:
            self.upload_status.emit("eQSL", "Failed: No credentials")
            return
            
        try:
            # We can use the simple ImportLog interface
            params = {
                'Callsign': user,
                'EQSL_PASSWORD': pwd,
                'Call': qso_data.get('CALL', ''),
                'QSO_DATE': qso_data.get('DATE', ''),
                'TIME_ON': qso_data.get('TIME', ''),
                'Band': qso_data.get('BAND', ''),
                'Mode': qso_data.get('MODE', ''),
                'RST_Sent': qso_data.get('RST_SENT', ''),
                'RST_Rcvd': qso_data.get('RST_RCVD', '')
            }
            url = "https://www.eqsl.cc/qslcard/ImportLog.cfm?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url, timeout=10) as response:
                result = response.read().decode('utf-8')
                if "successfully entered" in result.lower() or "ok" in result.lower():
                    self.upload_status.emit("eQSL", "Success")
                else:
                    self.upload_status.emit("eQSL", "Failed to confirm upload")
        except Exception as e:
            self.upload_status.emit("eQSL", f"Exception: {e}")
            
    def _upload_lotw(self, adif_file):
        tqsl_path = self.settings.get("lotw_path", "C:\\Program Files (x86)\\TrustedQSL\\tqsl.exe")
        if not os.path.exists(tqsl_path):
            self.upload_status.emit("LoTW", "Failed: tqsl.exe not found")
            return
            
        try:
            # tqsl -x (suppress prompts) -q (quiet) -u (upload) -a update (action update)
            cmd = [tqsl_path, "-x", "-q", "-u", "-a", "update", adif_file]
            
            # Using subprocess.run in a thread
            proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if proc.returncode == 0:
                self.upload_status.emit("LoTW", "Success (TQSL Uploaded)")
            else:
                # Truncate stderr just in case it's huge
                err = proc.stderr.strip()[:100]
                self.upload_status.emit("LoTW", f"Failed: Code {proc.returncode} {err}")
        except Exception as e:
            self.upload_status.emit("LoTW", f"Exception: {e}")
