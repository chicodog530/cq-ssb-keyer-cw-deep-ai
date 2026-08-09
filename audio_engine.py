import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import time
import os

ITU_PHONETICS = {
    'A': 'Alpha', 'B': 'Bravo', 'C': 'Charlie', 'D': 'Delta', 'E': 'Echo',
    'F': 'Foxtrot', 'G': 'Golf', 'H': 'Hotel', 'I': 'India', 'J': 'Juliet',
    'K': 'Kilo', 'L': 'Lima', 'M': 'Mike', 'N': 'November', 'O': 'Oscar',
    'P': 'Papa', 'Q': 'Quebec', 'R': 'Romeo', 'S': 'Sierra', 'T': 'Tango',
    'U': 'Uniform', 'V': 'Victor', 'W': 'Whiskey', 'X': 'X-ray', 'Y': 'Yankee',
    'Z': 'Zulu', '0': 'Zero', '1': 'One', '2': 'Two', '3': 'Three',
    '4': 'Four', '5': 'Five', '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine'
}

class AudioEngine:
    def __init__(self):
        self.stream = None
        self.monitor_stream = None
        self.is_recording = False
        self.is_playing = False
        self.is_monitoring = False
        self.is_live_mic = False
        self.monitor_volume = 1.0
        self.live_mic_stream = None
        
        self.audio_queue = queue.Queue()
        self.worker_thread = None
        
        self.current_peak = 0.0
        self.is_clipping = False
        
        self.playback_finished_callback = None
        
        # Scope Buffers
        self.scope_data_rx = np.zeros(512, dtype=np.float32)
        self.scope_data_tx = np.zeros(512, dtype=np.float32)

    def is_device_valid(self, device_index, kind):
        if device_index is None:
            return False
        try:
            sd.query_devices(device_index, kind)
            return True
        except:
            return False

    def set_playback_finished_callback(self, cb):
        self.playback_finished_callback = cb
        
    def start_recording(self, device_index, filename, samplerate=None, channels=1):
        if self.is_recording or self.is_playing:
            return False
            
        # Reset meters and scope
        self.current_peak = 0.0
        self.is_clipping = False
        self.scope_data_rx.fill(0)
            
        try:
            device_info = sd.query_devices(device_index, 'input')
            if samplerate is None:
                samplerate = int(device_info['default_samplerate'])
        except Exception as e:
            print(f"Error querying device: {e}")
            return False
            
        self.is_recording = True
        self.audio_queue = queue.Queue(maxsize=100) # Bounded queue
        self.dropped_buffers = 0
        
        def callback(indata, frames, time, status):
            if status:
                print(status)
            try:
                self.audio_queue.put_nowait(indata.copy())
            except queue.Full:
                self.dropped_buffers += 1
            
            # Metering
            peak = np.max(np.abs(indata))
            self.current_peak = peak
            
            # Scope Update (downsample/copy last 512 samples)
            if len(indata) >= 512:
                self.scope_data_rx[:] = indata[-512:, 0]
            else:
                self.scope_data_rx[:-len(indata)] = self.scope_data_rx[len(indata):]
                self.scope_data_rx[-len(indata):] = indata[:, 0]
                
            if peak >= 0.99:
                self.is_clipping = True

        try:
            self.stream = sd.InputStream(samplerate=samplerate, device=device_index,
                                         channels=channels, callback=callback)
            self.worker_thread = threading.Thread(target=self._file_writer, args=(filename, samplerate, channels))
            self.worker_thread.start()
            self.stream.start()
            return True
        except Exception as e:
            print(f"Error starting recording stream: {e}")
            self.is_recording = False
            return False
        
    def _file_writer(self, filename, samplerate, channels):
        # We use mode 'w' to overwrite atomically if it's a temp file
        with sf.SoundFile(filename, mode='w', samplerate=int(samplerate),
                          channels=channels, subtype='PCM_16', format='WAV') as file:
            while True:
                try:
                    data = self.audio_queue.get(timeout=0.1)
                    if data is None: # Sentinel received, drain complete
                        break
                    file.write(data)
                except queue.Empty:
                    if not self.is_recording:
                        break
                    continue
            if self.dropped_buffers > 0:
                print(f"Warning: {self.dropped_buffers} audio buffers were dropped during recording!")

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        try:
            self.audio_queue.put_nowait(None) # Send sentinel to drain queue
        except queue.Full:
            pass
            
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
            if self.worker_thread.is_alive():
                print("Error: Audio writer thread failed to terminate cleanly.")
            self.worker_thread = None
            
    def start_playback(self, device_index, filename, tx_gain_db=0):
        if self.is_recording or self.is_playing:
            return False
            
        # Reset meters and scope
        self.current_peak = 0.0
        self.is_clipping = False
        self.scope_data_tx.fill(0)
            
        try:
            data, fs = sf.read(filename, dtype='float32')
            
            if len(data) == 0:
                print("Error: Audio file is empty.")
                return False
            
            device_info = sd.query_devices(device_index, 'output')
            target_fs = int(device_info['default_samplerate'])
            
            # Stereo USB Support
            out_channels = min(2, device_info['max_output_channels'])
            
            # Auto-Resample
            if fs != target_fs:
                duration = len(data) / fs
                new_len = int(duration * target_fs)
                x_old = np.linspace(0, duration, len(data))
                x_new = np.linspace(0, duration, new_len)
                
                if len(data.shape) > 1:
                    new_data = np.zeros((new_len, data.shape[1]), dtype=np.float32)
                    for i in range(data.shape[1]):
                        new_data[:, i] = np.interp(x_new, x_old, data[:, i])
                    data = new_data
                else:
                    data = np.interp(x_new, x_old, data).astype(np.float32)
                fs = target_fs
            
            # Remove DC offset
            if len(data) > 0:
                data = data - np.mean(data)
                
            # Apply TX Gain (dB to linear)
            if len(data) > 0:
                linear_gain = 10 ** (tx_gain_db / 20.0)
                data = data * linear_gain
                
            # Hard Clip Guard (-1 dBFS = ~0.89)
            clip_limit = 0.89125
            if len(data) > 0:
                data = np.clip(data, -clip_limit, clip_limit)
                
            self.is_playing = True
            
            # Mono to Stereo duplication if required
            if len(data.shape) > 1:
                data = data[:, 0].reshape(-1, 1)
            else:
                data = data.reshape(-1, 1)
                
            if out_channels == 2:
                data = np.column_stack((data, data))
            
            def callback(outdata, frames, time, status):
                if status:
                    print(status)
                chunksize = min(len(data) - self.playback_pos, frames)
                
                chunk_data = data[self.playback_pos:self.playback_pos + chunksize]
                outdata[:chunksize] = chunk_data
                
                if chunksize < frames:
                    outdata[chunksize:] = 0
                    raise sd.CallbackStop
                self.playback_pos += chunksize
                
                # Metering post-gain
                if chunksize > 0:
                    peak = np.max(np.abs(chunk_data))
                    self.current_peak = peak
                    if peak >= clip_limit - 0.01:
                        self.is_clipping = True
                
                # Scope Update (use channel 0)
                if chunksize >= 512:
                    self.scope_data_tx[:] = outdata[-512:, 0]
                elif chunksize > 0:
                    self.scope_data_tx[:-chunksize] = self.scope_data_tx[chunksize:]
                    self.scope_data_tx[-chunksize:] = outdata[:chunksize, 0]

            self.playback_pos = 0

            self.stream = sd.OutputStream(samplerate=fs, device=device_index,
                                          channels=out_channels, callback=callback, finished_callback=self._playback_finished)
            self.stream.start()
            return True
        except Exception as e:
            print(f"Error starting playback: {e}")
            self.is_playing = False
            return False
            
    def _playback_finished(self):
        if not self.is_playing:
            return # Prevent double-firing
        self.is_playing = False
        
        cb = self.playback_finished_callback
        self.playback_finished_callback = None
        if cb:
            cb()

    def stop_playback(self):
        if self.is_playing and self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None
            self._playback_finished()

    def start_monitoring(self, rx_device, monitor_device, volume=1.0, samplerate=None, channels=1):
        if self.is_monitoring:
            return False
            
        self.monitor_volume = volume
        
        try:
            device_info = sd.query_devices(rx_device, 'input')
            if samplerate is None:
                samplerate = int(device_info['default_samplerate'])
                
            def callback(indata, outdata, frames, time, status):
                if status:
                    print(status)
                outdata[:] = indata * self.monitor_volume
                
                # Metering
                peak = np.max(np.abs(indata))
                self.current_peak = peak
                
                # Scope Update (same for rx during monitor)
                if len(indata) >= 512:
                    self.scope_data_rx[:] = indata[-512:, 0]
                else:
                    self.scope_data_rx[:-len(indata)] = self.scope_data_rx[len(indata):]
                    self.scope_data_rx[-len(indata):] = indata[:, 0]
                    
                if peak >= 0.99:
                    self.is_clipping = True

            self.monitor_stream = sd.Stream(device=(rx_device, monitor_device),
                                            samplerate=samplerate, channels=channels,
                                            callback=callback)
            self.monitor_stream.start()
            self.is_monitoring = True
            return True
        except Exception as e:
            print(f"Error starting monitoring loopback: {e}")
            return False

    def stop_monitoring(self):
        self.is_monitoring = False
        if self.monitor_stream:
            try:
                self.monitor_stream.abort()
            except Exception as e:
                print(f"Error aborting stream: {e}")
            try:
                self.monitor_stream.close()
            except:
                pass
            self.monitor_stream = None

    def start_live_mic(self, mic_device, tx_device, tx_gain_db=0):
        if self.is_recording or self.is_playing or getattr(self, 'is_live_mic', False):
            return False
            
        self.is_live_mic = True
        
        try:
            device_info = sd.query_devices(mic_device, 'input')
            samplerate = int(device_info['default_samplerate'])
            
            tx_info = sd.query_devices(tx_device, 'output')
            out_channels = min(2, tx_info['max_output_channels'])
            
            linear_gain = 10 ** (tx_gain_db / 20.0)
            clip_limit = 0.89125
            
            def callback(indata, outdata, frames, time, status):
                if status:
                    print(status)
                
                # Apply TX Gain
                processed = indata * linear_gain
                
                # Hard Clip Guard
                processed = np.clip(processed, -clip_limit, clip_limit)
                
                # Mono to Stereo duplication if required
                if len(processed.shape) > 1:
                    processed = processed[:, 0].reshape(-1, 1)
                else:
                    processed = processed.reshape(-1, 1)
                    
                if out_channels == 2:
                    processed = np.column_stack((processed, processed))
                
                outdata[:] = processed
                
                # Metering post-gain
                peak = np.max(np.abs(processed))
                self.current_peak = peak
                if peak >= clip_limit - 0.01:
                    self.is_clipping = True
                
                # Scope Update (use channel 0)
                if len(outdata) >= 512:
                    self.scope_data_tx[:] = outdata[-512:, 0]
                else:
                    self.scope_data_tx[:-len(outdata)] = self.scope_data_tx[len(outdata):]
                    self.scope_data_tx[-len(outdata):] = outdata[:, 0]

            self.live_mic_stream = sd.Stream(device=(mic_device, tx_device),
                                            samplerate=samplerate, channels=(1, out_channels),
                                            callback=callback)
            self.live_mic_stream.start()
            return True
        except Exception as e:
            print(f"Error starting live mic stream: {e}")
            self.is_live_mic = False
            return False

    def stop_live_mic(self):
        self.is_live_mic = False
        if hasattr(self, 'live_mic_stream') and self.live_mic_stream:
            try:
                self.live_mic_stream.abort()
                self.live_mic_stream.close()
            except:
                pass
            self.live_mic_stream = None

    def get_tts_voices(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            return [(v.id, v.name) for v in engine.getProperty('voices')]
        except:
            return []

    def generate_tts_wav(self, callsign, rst, filepath, custom_text=None, voice_id=None, rate=150):
        import pyttsx3
        engine = pyttsx3.init()
        
        if voice_id:
            try:
                engine.setProperty('voice', voice_id)
            except:
                pass
        else:
            # Try to find a good female voice or default to system default
            voices = engine.getProperty('voices')
            for voice in voices:
                if "Zira" in voice.name or "Female" in voice.name:
                    engine.setProperty('voice', voice.id)
                    break
                
        # Set speech rate
        engine.setProperty('rate', rate)
        
        if custom_text:
            text_to_speak = custom_text
        else:
            # Create phonetic callsign
            phonetic_call = []
            for char in callsign.upper():
                if char in ITU_PHONETICS:
                    phonetic_call.append(ITU_PHONETICS[char])
                elif char.strip():
                    phonetic_call.append(char)
                    
            spoken_call = " ".join(phonetic_call)
            
            # RST characters should be spoken as individual digits
            spoken_rst = " ".join(list(str(rst)))
            
            text_to_speak = f"{spoken_call}, you are {spoken_rst}."
            
        engine.save_to_file(text_to_speak, filepath)
        engine.runAndWait()
        
        return True
