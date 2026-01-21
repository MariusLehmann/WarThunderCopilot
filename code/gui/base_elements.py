from PySide6.QtWidgets import QLabel, QDockWidget, QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QBrush

from settings import WINDOW_UPDATE_INTERVALL, WINDOW_IDLE_UPDATE_INTERVALL

class CannotWorkException(Exception):
    """Base class For Exceptions which prevent a window from working"""
    pass
class SelectableLabel(QLabel):
    activated:bool
    name:str
    
    def __init__(self, name:str):
        super().__init__(f"  \t{name}")
        self.name = name
        self.activated = False
    
    def activate(self):
        if self.activated: 
            return
        self.setText(f"▶\t{self.name}")  
        self.setStyleSheet("font-weight: bold")
        self.activated = True  
    
    def deactivate(self):
        if not self.activated: 
            return
        self.setText(f"  \t{self.name}")
        self.setStyleSheet("font-weight: normal")
        self.activated = False
        
    def mark_safe(self):
        self.setStyleSheet("color: green")
    
    def mark_unsafe(self):
        self.setStyleSheet("color: gray")
        
class Lamp(QWidget):
    """Eine farbige Lampe mit Label darunter, responsive Größe."""
    def __init__(self, label, color_off=Qt.GlobalColor.gray, color_on=Qt.GlobalColor.green):
        super().__init__()
        self.color_off = QColor(color_off)
        self.color_on = QColor(color_on)
        self.state = False
        self.label_text = label
        self.setMinimumSize(40, 40)

    def set_state(self, on: bool):
        self.state = on
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        diameter = min(w, h) * 0.6
        x = (w - diameter) / 2
        y = (h - diameter) / 2 - 10  # Platz für Label

        brush = QBrush(self.color_on if self.state else self.color_off)
        painter.setBrush(brush)
        painter.drawEllipse(int(x), int(y), int(diameter), int(diameter))

        painter.drawText(0, int(y + diameter), w, h - int(y + diameter),
                         Qt.AlignmentFlag.AlignCenter, self.label_text)
class BasicDockWidget(QDockWidget):
    _update_timer:QTimer
    _elements:dict
    _inactive:bool
    
    def __init__(self, title="Basic Dock", *args, **kwargs):        
        super().__init__(title)
        
        self.setObjectName(title)
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
        self._elements = {}
        self._init_window(*args, **kwargs)
        
        self._inactive = False
        
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.__start_update_function)
        self._update_timer.setSingleShot(True)
        self._update_timer.start(WINDOW_UPDATE_INTERVALL)
        
    def _init_window(self, *args, **kwargs) -> None:
        raise NotImplementedError()
    
    def _update_window(self) -> None:
        raise NotImplementedError()
    
    def __start_update_function(self) -> None:
        try:
            self._update_window()
            self._update_timer.start(WINDOW_UPDATE_INTERVALL)
        except Exception as e:
            self._update_timer.start(WINDOW_IDLE_UPDATE_INTERVALL)
            raise e
        
    def set_to_inactive(self) -> None:
        self._inactive = True
        self._update_timer.stop()
        
    def set_to_active(self) -> None:
        self._inactive = False
        self.__start_update_function()
        
    def is_active(self):
        return not self._inactive