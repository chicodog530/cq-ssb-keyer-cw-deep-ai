import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QImage, QColor
from PySide6.QtCore import Qt, Signal

class WaterfallWidget(QWidget):
    frequencyClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        
        self.history_size = 150
        self.fft_size = 8192
        self.max_freq_display = 3000.0  # Only show 0 to 3000 Hz
        
        self.image = QImage(512, self.history_size, QImage.Format_RGB32)
        self.image.fill(QColor(0, 0, 0))
        
        self.current_sample_rate = 48000
        
        self.overlay_active = False
        self.overlay_min_hz = 0
        self.overlay_max_hz = 0
        self.overlay_is_dsp = False
        self.theme = "Classic"

    def set_theme(self, theme_name):
        self.theme = theme_name

    def set_overlay(self, active, min_hz=400, max_hz=1200, is_dsp=False):
        self.overlay_active = active
        self.overlay_min_hz = min_hz
        self.overlay_max_hz = max_hz
        self.overlay_is_dsp = is_dsp
        self.update()
        
    def update_waterfall(self, audio_chunk, sample_rate):
        if not self.isVisible():
            return
            
        self.current_sample_rate = sample_rate
        
        if len(audio_chunk) < self.fft_size:
            return
            
        # Take the most recent samples
        data = audio_chunk[-self.fft_size:]
        
        # Apply window
        window = np.hanning(self.fft_size)
        data = data * window
        
        # Compute FFT
        spectrum = np.fft.rfft(data)
        magnitudes = np.abs(spectrum)
        
        magnitudes[magnitudes == 0] = 1e-10
        magnitudes_db = 20 * np.log10(magnitudes)
        
        # Normalize
        min_db = -20
        max_db = 60
        norm_mag = np.clip((magnitudes_db - min_db) / (max_db - min_db), 0, 1)
        
        nyquist = sample_rate / 2
        freq_resolution = nyquist / (self.fft_size / 2)
        
        max_bin = int(self.max_freq_display / freq_resolution)
        max_bin = min(max_bin, self.fft_size // 2)
        
        if max_bin <= 0:
            return
            
        norm_mag = norm_mag[:max_bin]
        
        if self.image.width() != max_bin:
            self.image = QImage(max_bin, self.history_size, QImage.Format_RGB32)
            self.image.fill(QColor(0, 0, 0))
            
        painter = QPainter(self.image)
        painter.drawImage(0, 1, self.image, 0, 0, max_bin, self.history_size - 1)
        
        # Draw new line at top
        for x in range(max_bin):
            val = norm_mag[x]
            # Custom Heatmap (Black -> Blue -> Purple -> Red -> Yellow -> White)
            if self.theme == "Green Phosphor":
                if val < 0.8:
                    r, g, b = 0, int(val / 0.8 * 255), 0
                else:
                    v = (val - 0.8) * 5
                    r, g, b = int(v * 200), 255, int(v * 200)
            elif self.theme == "Monochrome":
                v = int(val * 255)
                r, g, b = v, v, v
            else:
                if val < 0.2:
                    r, g, b = 0, 0, int(val * 5 * 255)
                elif val < 0.4:
                    v = (val - 0.2) * 5
                    r, g, b = int(v * 128), 0, 255
                elif val < 0.6:
                    v = (val - 0.4) * 5
                    r, g, b = int(128 + v * 127), 0, int((1 - v) * 255)
                elif val < 0.8:
                    v = (val - 0.6) * 5
                    r, g, b = 255, int(v * 255), 0
                else:
                    v = (val - 0.8) * 5
                    r, g, b = 255, 255, int(v * 255)
                
            painter.setPen(QColor(r, g, b))
            painter.drawPoint(x, 0)
            
        painter.end()
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.fillRect(self.rect(), QColor(0,0,0))
        painter.drawImage(self.rect(), self.image)
        
        # Draw frequency markers
        painter.setPen(QColor(255, 255, 255, 150))
        for hz in range(0, int(self.max_freq_display) + 1, 500):
            x = int((hz / self.max_freq_display) * self.width())
            painter.drawLine(x, 0, x, self.height())
            if hz > 0:
                painter.drawText(x + 5, 15, f"{hz} Hz")
                
        # Draw overlay
        if self.overlay_active:
            x1 = int((self.overlay_min_hz / self.max_freq_display) * self.width())
            x2 = int((self.overlay_max_hz / self.max_freq_display) * self.width())
            w = max(1, x2 - x1)
            
            if self.overlay_is_dsp:
                painter.setPen(QColor(255, 0, 0, 200))
                painter.setBrush(QColor(255, 0, 0, 40))
            else:
                painter.setPen(QColor(0, 255, 0, 200))
                painter.setBrush(QColor(0, 255, 0, 40))
                
            painter.drawRect(x1, 0, w, self.height())
            
            if self.overlay_is_dsp:
                painter.setPen(QColor(255, 100, 100))
                painter.drawText(x1 + 2, self.height() - 5, "DSP")
            else:
                painter.setPen(QColor(100, 255, 100))
                painter.drawText(x1 + 2, self.height() - 5, "AI Focus Window")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.position().x()
            freq = int((x / self.width()) * self.max_freq_display)
            self.frequencyClicked.emit(freq)
