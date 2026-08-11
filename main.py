import sys
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPalette, QColor, QPixmap
from PySide6.QtCore import Qt
import time
from ui.main_window import MainWindow

def global_exception_handler(exctype, value, traceback):
    import traceback as tb
    import os
    app_data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'CQ Voice Keyer')
    if not os.path.exists(app_data_dir):
        try: os.makedirs(app_data_dir)
        except: pass
    log_file = os.path.join(app_data_dir, "crash.log")
    try:
        with open(log_file, "w") as f:
            f.write("Uncaught Exception:\n")
            tb.print_exception(exctype, value, traceback, file=f)
    except:
        pass
    sys.__excepthook__(exctype, value, traceback)

sys.excepthook = global_exception_handler

def main():
    app = QApplication(sys.argv)
    
    # Modern Dark Theme
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.ToolTipBase, QColor(220, 220, 220))
    palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
    palette.setColor(QPalette.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    # Load settings to check if splash screen is enabled
    from settings_manager import SettingsManager
    temp_settings = SettingsManager()
    
    import os
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    splash_image_path = os.path.join(base_dir, 'UniversalRadio_Splash_800x600.png')
    
    splash = None
    if temp_settings.get("show_splash", True) and os.path.exists(splash_image_path):
        pixmap = QPixmap(splash_image_path)
        pixmap = pixmap.scaled(640, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
        splash.show()
        app.processEvents()
        
        end_time = time.time() + 3.0
        while time.time() < end_time:
            app.processEvents()
            time.sleep(0.01)
            
    window = MainWindow()
    window.show()
    
    if splash:
        splash.finish(window)
        
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
