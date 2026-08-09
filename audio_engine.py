import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import time

class AudioEngine:
    def __init__(self):
        self.stream = None
        self.monitor_stream = None
        self.is_recording = False
        self.is_playing = False
        self.is_monitoring = False
        
        self.audio_queue = queue.Queue()
        self.worker_thread = None
        
        self.current_peak = 0.0
        self.is_clipping = False
        
        self.playback_finished_callback = None
        
        # Scope Buffers
        self.scope_data_rx = np.zeros(512, dtype=np.float32)
        self.scope_data_tx = np.zeros(512, dtype=np.float32)

    def set_playback_finished_callback(self, cb):
        self.playback_finished_callback = cb
        
    def start_recording(self, device_index, filename, samplerate=None, channels=1):
        if self.is_recording or self.is_playing:
            return False
            
        try:
            device_info = sd.query_devices(device_index, 'input')
            if samplerate is None:
                samplerate = int(device_info['default_samplerate'])
        except Exception as e:
            print(f"Error querying device: {e}")
            return False
            
        self.is_recording = True
        self.audio_queue = queue.Queue()
        
        def callback(indata, frames, time, status):
            if status:
                print(status)
            self.audio_queue.put(indata.copy())
            
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
        with sf.SoundFile(filename, mode='x', samplerate=int(samplerate),
                          channels=channels, subtype='PCM_16') as file:
            while self.is_recording:
                try:
                    data = self.audio_queue.get(timeout=0.1)
                    file.write(data)
                except queue.Empty:
                    continue

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.worker_thread:
            self.worker_thread.join()
            
    def start_playback(self, device_index, filename):
        if self.is_recording or self.is_playing:
            return False
            
        try:
            data, fs = sf.read(filename, dtype='float32')
            
            # Remove DC offset (critical for cheap PC mics)
            data = data - np.mean(data)
            
            # Auto-normalize audio to 0.95 peak for strong, consistent modulation
            peak = np.max(np.abs(data))
            if peak > 0.0:
                data = data * (0.95 / peak)
                
            self.is_playing = True
            
            def callback(outdata, frames, time, status):
                if status:
                    print(status)
                chunksize = min(len(data) - self.playback_pos, frames)
                outdata[:chunksize] = data[self.playback_pos:self.playback_pos + chunksize]
                if chunksize < frames:
                    outdata[chunksize:] = 0
                    raise sd.CallbackStop
                self.playback_pos += chunksize
                
                # Scope Update
                if chunksize >= 512:
                    self.scope_data_tx[:] = outdata[-512:, 0]
                elif chunksize > 0:
                    self.scope_data_tx[:-chunksize] = self.scope_data_tx[chunksize:]
                    self.scope_data_tx[-chunksize:] = outdata[:chunksize, 0]

            self.playback_pos = 0
            # Mono playback
            if len(data.shape) > 1:
                data = data[:, 0].reshape(-1, 1)
            else:
                data = data.reshape(-1, 1)

            self.stream = sd.OutputStream(samplerate=fs, device=device_index,
                                          channels=1, callback=callback, finished_callback=self._playback_finished)
            self.stream.start()
            return True
        except Exception as e:
            print(f"Error starting playback: {e}")
            self.is_playing = False
            return False
            
    def _playback_finished(self):
        self.is_playing = False
        if self.stream:
            self.stream.close()
            self.stream = None
        
        if self.playback_finished_callback:
            self.playback_finished_callback()

    def stop_playback(self):
        if self.is_playing and self.stream:
            self.stream.stop()
            self._playback_finished()

    def start_monitoring(self, rx_device, monitor_device, samplerate=None, channels=1):
        if self.is_monitoring:
            return False
            
        try:
            device_info = sd.query_devices(rx_device, 'input')
            if samplerate is None:
                samplerate = int(device_info['default_samplerate'])
                
            def callback(indata, outdata, frames, time, status):
                if status:
                    print(status)
                outdata[:] = indata
                
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
            except Exception as e:
                print(f"Error closing stream: {e}")
            self.monitor_stream = None
