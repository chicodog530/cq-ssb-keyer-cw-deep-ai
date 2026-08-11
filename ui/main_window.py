from PySide6.QtWidgets import QMainWindow, QTabWidget
from ui.dashboard_tab import DashboardTab
from ui.cw_tab import CWTab
from ui.settings_tab import SettingsTab
from audio_engine import AudioEngine
from audio_devices import AudioDeviceManager
from settings_manager import SettingsManager
from rig_control import RigController
from tx_state import CQSequenceManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal Radio Audio Recorder & CQ Voice Keyer")
        self.resize(800, 600)
        
        # Core Systems
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioDeviceManager()
        self.audio_engine = AudioEngine()
        self.rig_controller = RigController(settings_manager=self.settings_manager)
        self.sequence_manager = CQSequenceManager(self.rig_controller, self.audio_engine, self.settings_manager)
        
        # Load DeepCW
        import os
        import sys
        from deepcw_engine import DeepCWEngine
        try:
            if hasattr(sys, '_MEIPASS'):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.cw_engine = DeepCWEngine(
                os.path.join(base_dir, 'models', 'model.onnx'), 
                os.path.join(base_dir, 'models', 'model.onnx.json')
            )
        except Exception as e:
            print("Could not load DeepCW engine:", e)
            self.cw_engine = None
            
        # Start background workers
        self.rig_controller.start()
        
        # UI Setup
        self.tabs = QTabWidget()
        
        from ui.logger_tab import LoggerTab
        self.dashboard_tab = DashboardTab(self.audio_engine, self.settings_manager, self.rig_controller, self.sequence_manager, self.cw_engine)
        self.cw_tab = CWTab(self.audio_engine, self.settings_manager, self.sequence_manager, self.cw_engine)
        self.logger_tab = LoggerTab(self.rig_controller)
        self.settings_tab = SettingsTab(self.audio_manager, self.settings_manager, self.rig_controller)
        
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.cw_tab, "CW & Waterfall")
        self.tabs.addTab(self.logger_tab, "QSO Logbook")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        self.setCentralWidget(self.tabs)

    def closeEvent(self, event):
        self.sequence_manager.abort()
        self.audio_engine.stop_recording()
        self.audio_engine.stop_playback()
        self.audio_engine.stop_monitoring()
        self.rig_controller.stop()
        super().closeEvent(event)
