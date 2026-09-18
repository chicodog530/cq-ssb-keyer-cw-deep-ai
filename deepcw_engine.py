import json
import math
from pathlib import Path
import threading

import numpy as np
import onnxruntime as ort

class DeepCWEngine:
    def __init__(self, model_path: str, metadata_path: str):
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)
        
        with self.metadata_path.open("r", encoding="utf-8") as file:
            self.metadata = json.load(file)
            
        self.target_rate = int(self.metadata["sample_rate"])
        
        # Load ONNX session
        self.session = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
        
        self.lock = threading.Lock()
        
    def resample_linear(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        if source_rate == target_rate:
            return audio.astype(np.float32, copy=False)
        if len(audio) == 0:
            return audio.astype(np.float32, copy=False)

        target_length = int(round(len(audio) * target_rate / source_rate))
        source_positions = np.arange(target_length, dtype=np.float64) * source_rate / target_rate
        left = np.floor(source_positions).astype(np.int64)
        right = np.minimum(left + 1, len(audio) - 1)
        fraction = (source_positions - left).astype(np.float32)
        resampled = audio[left] * (1.0 - fraction) + audio[right] * fraction
        return resampled.astype(np.float32, copy=False)

    def frequency_bin_range(self, sample_rate: int, fft_length: int, min_hz: float, max_hz: float) -> tuple[int, int]:
        bin_hz = sample_rate / fft_length
        start_bin = int(math.ceil(min_hz / bin_hz))
        stop_bin = int(math.floor(max_hz / bin_hz)) + 1
        return start_bin, stop_bin

    def audio_to_spectrogram(self, audio: np.ndarray, center_freq: float = None) -> np.ndarray:
        fft_length = int(self.metadata["fft_length"])
        hop_length = int(self.metadata["hop_length"])
        sample_rate = int(self.metadata["sample_rate"])
        min_hz = float(self.metadata["spectrogram_min_freq_hz"])
        max_hz = float(self.metadata["spectrogram_max_freq_hz"])
        expected_bins = int(self.metadata["spectrogram_frequency_bins"])

        if center_freq is not None:
            default_center = (min_hz + max_hz) / 2.0
            shift = center_freq - default_center
            min_hz += shift
            max_hz += shift

        if len(audio) < fft_length:
            # Not enough audio
            return None

        start_bin, stop_bin = self.frequency_bin_range(sample_rate, fft_length, min_hz, max_hz)
        
        spectrum_len = (fft_length // 2) + 1
        
        slice_start = max(0, start_bin)
        slice_stop = min(spectrum_len, start_bin + expected_bins)
        
        pad_before = max(0, -start_bin)
        pad_after = max(0, (start_bin + expected_bins) - spectrum_len)

        pad = fft_length // 2
        audio = np.pad(audio, (pad, pad), mode="reflect")
        window = np.hanning(fft_length + 1)[:-1].astype(np.float32)
        frames = 1 + (len(audio) - fft_length) // hop_length
        spectrogram = np.empty((frames, expected_bins), dtype=np.float32)

        for frame_index in range(frames):
            start = frame_index * hop_length
            frame = audio[start : start + fft_length] * window
            spectrum = np.fft.rfft(frame, n=fft_length)
            
            spectrum_slice = np.abs(spectrum[slice_start:slice_stop]).astype(np.float32)
            if pad_before > 0 or pad_after > 0:
                spectrum_slice = np.pad(spectrum_slice, (pad_before, pad_after), 'constant')
                
            spectrogram[frame_index] = spectrum_slice

        if self.metadata.get("normalization") == "log1p":
            spectrogram = np.log1p(spectrogram, dtype=np.float32)

        return spectrogram[np.newaxis, np.newaxis, :, :].astype(np.float32, copy=False)

    def greedy_ctc_decode(self, log_probs: np.ndarray) -> str:
        chars = list(self.metadata["chars"])
        blank_index = int(self.metadata["blank_index"])
        best_path = log_probs[0].argmax(axis=-1)
        decoded: list[str] = []
        previous: int = None

        for index in best_path:
            index = int(index)
            if index == blank_index:
                previous = None
                continue
            if index != previous:
                decoded.append(chars[index])
            previous = index

        return "".join(decoded)

    def decode(self, audio: np.ndarray, source_rate: int, center_freq: float = None) -> str:
        """
        Decodes a block of audio. 
        Audio should be a 1D float32 array in the range [-1.0, 1.0].
        Minimum recommended length is 5 seconds of audio.
        """
        with self.lock:
            # Ensure audio is float32
            audio = audio.astype(np.float32, copy=False)
            
            # Resample to the rate the model expects (usually 8000)
            resampled_audio = self.resample_linear(audio, source_rate, self.target_rate)
            
            spectrogram = self.audio_to_spectrogram(resampled_audio, center_freq)
            if spectrogram is None:
                return ""
                
            outputs = self.session.run(
                [self.metadata["onnx_output_name"]], 
                {self.metadata["onnx_input_name"]: spectrogram}
            )
            
            return self.greedy_ctc_decode(outputs[0])
