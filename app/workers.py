from threading import Event
from PySide6.QtCore import QThread, Signal
from .sources import CancelledError


class Worker(QThread):
    result = Signal(object)
    failed = Signal(str)
    delta = Signal(str)
    progress = Signal(int, int)

    def __init__(self, task, parent=None, allow_partial=False):
        super().__init__(parent)
        self.task = task
        self.allow_partial = allow_partial
        self.cancelled = Event()

    def run(self):
        try:
            result = self.task(self.cancelled.is_set, self.progress.emit, self.delta.emit)
            if self.cancelled.is_set() and not (self.allow_partial and isinstance(result, dict) and result.get("status") == "incomplete"):
                raise CancelledError("Đã hủy; kết quả chưa hoàn tất không được sử dụng.")
            self.result.emit(result)
        except Exception as error:
            self.failed.emit(str(error))
