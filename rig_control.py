import socket
import threading
import time
import subprocess
import os

class RigController:
    def __init__(self, host="127.0.0.1", port=4532, settings_manager=None):
        self.host = host
        self.port = port
        self.settings_manager = settings_manager
        
        self.connected = False
        self.frequency = "Unknown"
        self.mode = "Unknown"
        self.ptt_state = False
        self.last_error = ""
        
        self.sock = None
        self._running = False
        self._thread = None
        self._rigctld_process = None
        
        self._pause_polling = False
        self._lock = threading.Lock()
        
    @staticmethod
    def get_models():
        exe_path = os.path.join(os.getcwd(), "rigctld", "rigctld-wsjtx.exe")
        models = []
        if not os.path.exists(exe_path):
            return models
        try:
            output = subprocess.check_output([exe_path, "-l"], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            for line in output.split('\n'):
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0].isdigit():
                    model_id = parts[0]
                    # Mfg Model...
                    name = " ".join(parts[1:3])
                    models.append((model_id, name))
        except Exception as e:
            print(f"Error getting rig models: {e}")
        return models

    def start(self):
        if self._running:
            return
            
        self._start_rigctld_process()
            
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _log(self, msg):
        with open("rigctld_debug.log", "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
        print(msg)

    def _start_rigctld_process(self):
        if self._rigctld_process:
            try:
                self._rigctld_process.kill()
                self._log("Killed old rigctld process")
            except:
                pass
                
        if not self.settings_manager:
            return
            
        model = self.settings_manager.get("rig_model", "1")
        com_port = self.settings_manager.get("rig_com_port", "")
        baud = self.settings_manager.get("rig_baud", "4800")
        
        data_bits = self.settings_manager.get("rig_data_bits", "Default")
        stop_bits = self.settings_manager.get("rig_stop_bits", "Default")
        handshake = self.settings_manager.get("rig_handshake", "Default")
        dtr = self.settings_manager.get("rig_dtr", "Default")
        rts = self.settings_manager.get("rig_rts", "Default")
        
        conf = []
        if data_bits != "Default": conf.append(f"data_bits={data_bits}")
        if stop_bits != "Default": conf.append(f"stop_bits={stop_bits}")
        if handshake != "Default": conf.append(f"serial_handshake={handshake}")
        if dtr == "High": conf.append("dtr_state=ON")
        elif dtr == "Low": conf.append("dtr_state=OFF")
        if rts == "High": conf.append("rts_state=ON")
        elif rts == "Low": conf.append("rts_state=OFF")
        
        exe_path = os.path.join(os.getcwd(), "rigctld", "rigctld-wsjtx.exe")
        self._log(f"Starting rigctld. Exists: {os.path.exists(exe_path)}")
        if os.path.exists(exe_path) and com_port:
            try:
                # -m model -r com_port -s baud -t tcp_port
                args = [exe_path, "-m", str(model), "-r", com_port, "-s", str(baud), "-t", str(self.port)]
                if conf:
                    args.extend(["-C", ",".join(conf)])
                self._rigctld_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self._log(f"Started bundled rigctld with args: {args}")
            except Exception as e:
                self._rigctld_process = None
                self._log(f"Error starting rigctld: {e}")
                self.last_error = f"Failed to start rigctld: {e}"

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        self._disconnect()
        
        if self._rigctld_process:
            try:
                self._rigctld_process.kill()
            except:
                pass
            self._rigctld_process = None

    def _connect(self):
        self._log(f"Attempting _connect to {self.host}:{self.port}")
        try:
            # Try IPv4 first
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2.0)
            self.sock.connect((self.host, self.port))
            self.connected = True
            self.last_error = ""
            self._log("IPv4 connect SUCCESS")
        except socket.timeout:
            self.connected = False
            self.last_error = "Connection to rigctld timed out. (Is it blocked by firewall?)"
            self.sock = None
            self._log("IPv4 connect TIMED OUT")
        except Exception as e:
            self._log(f"IPv4 connect FAILED: {e}")
            # Fallback to IPv6 if localhost resolves to ::1
            try:
                self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                self.sock.settimeout(2.0)
                self.sock.connect(("::1", self.port))
                self.connected = True
                self.last_error = ""
                self._log("IPv6 connect SUCCESS")
            except Exception as e2:
                self.connected = False
                self.last_error = f"Connection failed: {str(e2)}"
                self.sock = None
                self._log(f"IPv6 connect FAILED: {e2}")

    def _disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        self.connected = False

    def _send_cmd(self, cmd):
        if not self.sock:
            return None
        try:
            self.sock.sendall((cmd + "\n").encode('utf-8'))
            data = self.sock.recv(1024)
            return data.decode('utf-8').strip()
        except socket.timeout:
            self.connected = False
            self.last_error = f"Command '{cmd}' timed out! Radio is not responding to rigctld. Check Baud, DTR/RTS, or if radio is ON."
            self.sock = None
            return None
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            self.sock = None
            return None

    def _poll_loop(self):
        while self._running:
            if self._pause_polling:
                time.sleep(0.5)
                continue
                
            with self._lock:
                if not self.connected:
                    self._connect()
                    
                if not self.connected:
                    pass
                else:
                    # Poll Frequency
                    freq = self._send_cmd("f")
                    if freq:
                        self.frequency = freq

                    # Poll Mode
                    mode = self._send_cmd("m")
                    if mode:
                        parts = mode.split('\n')
                        if parts:
                            self.mode = parts[0]

                    # Poll PTT
                    ptt = self._send_cmd("t")
                    if ptt:
                        self.ptt_state = (ptt == "1")

            time.sleep(0.4) # Poll roughly 2.5 times a second

    def set_ptt(self, state):
        with self._lock:
            val = "1" if state else "0"
            res = self._send_cmd(f"T {val}")
            if res == "RPRT 0":
                self.ptt_state = state
                return True
            return False

    def test_cat(self):
        self._pause_polling = True
        try:
            with self._lock:
                self._disconnect()
                self._start_rigctld_process()
                time.sleep(2.5) # Give it time to initialize and grab the COM port
                
                if not self._rigctld_process:
                    if not self.last_error:
                        self.last_error = "rigctld-wsjtx.exe process failed to start completely. Is the rigctld folder missing?"
                    return False
                    
                if self._rigctld_process.poll() is not None:
                    self.last_error = f"rigctld process exited prematurely (code {self._rigctld_process.returncode}). Check settings."
                    return False
                    
                self._connect()
                if not self.connected:
                    return False
                    
                res = self._send_cmd("f")
                return res is not None and res.strip() != ""
        finally:
            self._pause_polling = False

    def set_frequency(self, freq_hz):
        res = self._send_cmd(f"F {freq_hz}")
        if res == "RPRT 0":
            self.frequency = str(freq_hz)
            return True
        return False

