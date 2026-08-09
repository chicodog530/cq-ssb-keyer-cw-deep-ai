from PySide6.QtCore import QObject, Signal, QTimer
import time

class SequenceState:
    IDLE = 0
    PRE_ROLL = 1
    TX_AUDIO = 2
    POST_ROLL = 3
    INTERVAL_WAIT = 4
    VERIFYING = 5
    ERROR = 6

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
        
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.setSingleShot(True)
        self.watchdog_timer.timeout.connect(self._on_watchdog_timeout)
        
        self.audio_finished_signal.connect(self.next_phase_after_audio)

    def start_sequence(self, audio_file, repeat_enabled=False, max_repeats=3, repeat_interval_ms=10000):
        if self.state not in (SequenceState.IDLE, SequenceState.ERROR):
            return False
            
        tx_idx = self.settings_manager.get("tx_output_index")
        if tx_idx is None:
            self.state = SequenceState.ERROR
            self.state_changed.emit(self.state, "Error: Select TX Output in Settings first")
            return False
            
        self.tx_device_idx = tx_idx
        self.current_file = audio_file
        
        self.repeat_enabled = repeat_enabled
        self.max_repeats = max_repeats if max_repeats > 0 else 3 # finite default
        self.current_repeat = 1
        self.repeat_interval_ms = repeat_interval_ms
        
        self._transition_to_verifying()
        return True
        
    def _on_watchdog_timeout(self):
        self.state = SequenceState.ERROR
        self.state_changed.emit(self.state, "Error: TX Watchdog Timeout! (60s max)")
        self.abort()

    def abort(self):
        try:
            self.timer.stop()
            self.watchdog_timer.stop()
            self.audio_engine.stop_playback()
        finally:
            # Guaranteed PTT off attempt
            try:
                if self.rig_controller.connected:
                    self.rig_controller.set_ptt(False)
            except Exception as e:
                print(f"Failed to set PTT off during abort: {e}")
                
        if self.state != SequenceState.ERROR:
            self.state = SequenceState.IDLE
            self.state_changed.emit(self.state, "Sequence Aborted")
            
        self.sequence_finished.emit()

    def _transition_to_verifying(self):
        self.state = SequenceState.VERIFYING
        self.state_changed.emit(self.state, "Verifying Rig Connection...")
        
        if not self.rig_controller.connected:
            self.state = SequenceState.ERROR
            self.state_changed.emit(self.state, "Error: Rig disconnected")
            self.abort()
            return
            
        if self.rig_controller.ptt_state:
            self.state = SequenceState.ERROR
            self.state_changed.emit(self.state, "Error: PTT is already active")
            self.abort()
            return
            
        # Try to set PTT On and wait for RPRT 0
        success = self.rig_controller.set_ptt(True)
        if not success:
            self.state = SequenceState.ERROR
            self.state_changed.emit(self.state, "Error: Rig rejected PTT ON command")
            self.abort()
            return
            
        # Start watchdog the moment PTT is enabled
        self.watchdog_timer.start(60000)
        self._transition_to_pre_roll()

    def _transition_to_pre_roll(self):
        self.state = SequenceState.PRE_ROLL
        msg = "Pre-Roll (PTT Keyed)..."
        if self.repeat_enabled:
            msg += f" [Repeat {self.current_repeat}/{self.max_repeats}]"
        self.state_changed.emit(self.state, msg)
        
        pre_roll_delay = int(self.settings_manager.get("tx_pre_roll_ms", 200))
        self.timer.start(pre_roll_delay)

    def _on_timer_complete(self):
        if self.state == SequenceState.PRE_ROLL:
            self._transition_to_tx_audio()
        elif self.state == SequenceState.POST_ROLL:
            self._transition_to_interval_or_idle()
        elif self.state == SequenceState.INTERVAL_WAIT:
            self.current_repeat += 1
            self._transition_to_verifying()

    def _transition_to_tx_audio(self):
        self.state = SequenceState.TX_AUDIO
        self.state_changed.emit(self.state, "Transmitting Audio...")
        
        self.audio_engine.set_playback_finished_callback(self._on_audio_finished)
        
        tx_gain_db = self.settings_manager.get("tx_gain_db", -6)
        success = self.audio_engine.start_playback(self.tx_device_idx, self.current_file, tx_gain_db)
        if not success:
            self.state = SequenceState.ERROR
            self.state_changed.emit(self.state, "Error starting playback")
            self.abort()

    def _on_audio_finished(self):
        self.audio_finished_signal.emit()

    def next_phase_after_audio(self):
        if self.state != SequenceState.TX_AUDIO:
            return
            
        self.state = SequenceState.POST_ROLL
        self.state_changed.emit(self.state, "Post-Roll (Waiting to unkey)...")
        post_roll_delay = int(self.settings_manager.get("tx_post_roll_ms", 100))
        self.timer.start(post_roll_delay)

    def _transition_to_interval_or_idle(self):
        # Stop watchdog since we are dropping PTT
        self.watchdog_timer.stop()
        
        if self.rig_controller.connected:
            self.rig_controller.set_ptt(False)
            
        if self.repeat_enabled and self.current_repeat < self.max_repeats:
            self.state = SequenceState.INTERVAL_WAIT
            self.state_changed.emit(self.state, f"Waiting {self.repeat_interval_ms/1000}s for next sequence...")
            self.timer.start(self.repeat_interval_ms)
        else:
            self.state = SequenceState.IDLE
            self.state_changed.emit(self.state, "Sequence Finished")
            self.sequence_finished.emit()
