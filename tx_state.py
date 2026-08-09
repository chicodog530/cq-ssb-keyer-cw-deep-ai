from PySide6.QtCore import QObject, Signal, QTimer
import time

class SequenceState:
    IDLE = 0
    PRE_ROLL = 1
    TX_AUDIO = 2
    POST_ROLL = 3
    INTERVAL_WAIT = 4

class CQSequenceManager(QObject):
    # Signals to update UI safely
    state_changed = Signal(int, str)
    sequence_finished = Signal()
    audio_finished_signal = Signal()
    
    def __init__(self, rig_controller, audio_engine, settings_manager):
        super().__init__()
        self.rig_controller = rig_controller
        self.audio_engine = audio_engine
        self.settings_manager = settings_manager
        
        self.state = SequenceState.IDLE
        
        self.current_file = ""
        self.tx_device_idx = None
        
        # Repetition tracking
        self.repeat_enabled = False
        self.max_repeats = 1
        self.current_repeat = 0
        self.repeat_interval_ms = 10000
        
        # Timers
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._on_timer_complete)
        
        self.audio_finished_signal.connect(self.next_phase_after_audio)

    def start_sequence(self, audio_file, repeat_enabled=False, max_repeats=1, repeat_interval_ms=10000):
        if self.state != SequenceState.IDLE:
            return False
            
        tx_idx = self.settings_manager.get("tx_output_index")
        if tx_idx is None:
            self.state_changed.emit(self.state, "Error: Select TX Output in Settings first")
            return False
            
        self.tx_device_idx = tx_idx
        self.current_file = audio_file
        
        self.repeat_enabled = repeat_enabled
        self.max_repeats = max_repeats
        self.current_repeat = 1
        self.repeat_interval_ms = repeat_interval_ms
        
        self._transition_to_pre_roll()
        return True
        
    def abort(self):
        self.timer.stop()
        self.audio_engine.stop_playback()
        if self.rig_controller.connected:
            self.rig_controller.set_ptt(False)
            
        self.state = SequenceState.IDLE
        self.state_changed.emit(self.state, "Sequence Aborted")
        self.sequence_finished.emit()

    def _transition_to_pre_roll(self):
        self.state = SequenceState.PRE_ROLL
        msg = "Pre-Roll (PTT Keyed)..."
        if self.repeat_enabled:
            msg += f" [Repeat {self.current_repeat}/{self.max_repeats if self.max_repeats > 0 else 'Infinite'}]"
        self.state_changed.emit(self.state, msg)
        
        if self.rig_controller.connected:
            self.rig_controller.set_ptt(True)
            
        pre_roll_delay = int(self.settings_manager.get("tx_pre_roll_ms", 200))
        self.timer.start(pre_roll_delay)

    def _on_timer_complete(self):
        if self.state == SequenceState.PRE_ROLL:
            self._transition_to_tx_audio()
        elif self.state == SequenceState.POST_ROLL:
            self._transition_to_interval_or_idle()
        elif self.state == SequenceState.INTERVAL_WAIT:
            self.current_repeat += 1
            self._transition_to_pre_roll()

    def _transition_to_tx_audio(self):
        self.state = SequenceState.TX_AUDIO
        self.state_changed.emit(self.state, "Transmitting Audio...")
        
        self.audio_engine.set_playback_finished_callback(self._on_audio_finished)
        
        success = self.audio_engine.start_playback(self.tx_device_idx, self.current_file)
        if not success:
            self.state_changed.emit(self.state, "Error starting playback")
            self.abort()

    def _on_audio_finished(self):
        # Called by audio engine thread. Emitting a signal safely hops to the main thread.
        self.audio_finished_signal.emit()

    def next_phase_after_audio(self):
        if self.state != SequenceState.TX_AUDIO:
            return
            
        self.state = SequenceState.POST_ROLL
        self.state_changed.emit(self.state, "Post-Roll (Waiting to unkey)...")
        post_roll_delay = int(self.settings_manager.get("tx_post_roll_ms", 100))
        self.timer.start(post_roll_delay)

    def _transition_to_interval_or_idle(self):
        if self.rig_controller.connected:
            self.rig_controller.set_ptt(False)
            
        if self.repeat_enabled and (self.max_repeats == 0 or self.current_repeat < self.max_repeats):
            self.state = SequenceState.INTERVAL_WAIT
            self.state_changed.emit(self.state, f"Waiting {self.repeat_interval_ms/1000}s for next sequence...")
            self.timer.start(self.repeat_interval_ms)
        else:
            self.state = SequenceState.IDLE
            self.state_changed.emit(self.state, "Sequence Finished")
            self.sequence_finished.emit()
