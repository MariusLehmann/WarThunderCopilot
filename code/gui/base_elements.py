from PySide6.QtWidgets import QLabel, QDockWidget, QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QBrush

from settings import WINDOW_UPDATE_INTERVALL, WINDOW_IDLE_UPDATE_INTERVALL

from enum import Enum


class CannotWorkException(Exception):
    """Base class For Exceptions which prevent a window from working"""
    pass
class SelectableLabel(QLabel):
    activated:bool
    name:str
    
    def __init__(self, id, name:str):
        super().__init__(f"  \t{name}")
        self.id = id
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

class LampState(Enum):
    OFF = 0
    ON = 1
    BLINKING = 2
    ALERT = 3


class Lamp(QWidget):
    """Eine farbige Lampe mit Label darunter, responsive Größe."""
    def __init__(self, label, color_off=Qt.GlobalColor.gray, color_on=Qt.GlobalColor.green, *,color_alert=Qt.GlobalColor.red, alert_blinking=True, blink_ratio=0.5, blink_interval=500, minimum_size=40):
        super().__init__()
        self.color_off = QColor(color_off)
        self.color_on = QColor(color_on)
        self.color_alert = QColor(color_alert)
        self.alert_blinking = alert_blinking

        self.blink_ratio, self.blink_interval = blink_ratio, blink_interval

        self.state = LampState.OFF
        self.label_text = label
        self.setMinimumSize(minimum_size, minimum_size)

        self._blink_on = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)

    def set_state(self, state: LampState):
        # Abwärtskompatibel: bool wird weiterhin als ON/OFF interpretiert.
        if not isinstance(state, LampState):
            state = LampState.ON if state else LampState.OFF

        
        if self.state != state:
            self.state = state
            if state == LampState.BLINKING or (state == LampState.ALERT and self.alert_blinking):
                self._blink_on = True
                self._restart_blink_timer()
            else:
                self._blink_timer.stop()
                self._blink_on = True

            self.update()

    def _restart_blink_timer(self):
        on_ms = self.blink_interval * self.blink_ratio
        self._blink_timer.start(int(on_ms if self._blink_on else self.blink_interval - on_ms))

    def _toggle_blink(self):
        self._blink_on = not self._blink_on
        self._restart_blink_timer()
        self.update()

    def _current_color(self) -> QColor:
        if self.state == LampState.OFF:
            return self.color_off
        if self.state == LampState.ON:
            return self.color_on
        if self.state == LampState.BLINKING:
            return self.color_on if self._blink_on else self.color_off
        if self.state == LampState.ALERT:
            if self.alert_blinking:
                return self.color_alert if self._blink_on else self.color_off
            return self.color_alert
        return self.color_off

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        diameter = min(w, h) * 0.6
        x = (w - diameter) / 2
        y = (h - diameter) / 2 - 10  # Platz für Label

        brush = QBrush(self._current_color())
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