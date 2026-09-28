from pathlib import Path
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioInput, QMediaCaptureSession, QMediaRecorder

class VoiceRecorder(QObject):
    started = Signal()
    stopped = Signal(str)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = QMediaCaptureSession()
        self.audio_input = QAudioInput()
        self.recorder = QMediaRecorder()
        self.session.setAudioInput(self.audio_input)
        self.session.setRecorder(self.recorder)
        self.recorder.errorOccurred.connect(lambda _error, message: self.error.emit(message or "Microphone recording error."))
        self.recorder.recorderStateChanged.connect(self._state_changed)
        self._path: Path | None = None

    def start(self, path: Path):
        if not self.recorder.isAvailable():
            self.error.emit("Audio recording is not available on this system.")
            return
        self._path = path
        self.recorder.setOutputLocation(QUrl.fromLocalFile(str(path)))
        self.recorder.record()
        self.started.emit()

    def stop(self):
        if self.recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            self.recorder.stop()

    def _state_changed(self, state):
        if state == QMediaRecorder.RecorderState.StoppedState and self._path:
            path = str(self._path)
            self._path = None
            self.stopped.emit(path)
