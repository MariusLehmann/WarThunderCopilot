from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QGroupBox
from PySide6.QtCore import Qt, QTimer, Slot

from enum import Enum

from gui.base_elements import SelectableLabel, Lamp, LampState

from Models import Plane, TelemetryData


from wt_dataclasses import FlapState, ValueHistory

FlapStateDisplayText = {
    FlapState.COMBAT.value: "Kampf",
    FlapState.START.value: "Start",
    FlapState.LANDING.value: "Landung"
     
}


class FlapValueException(ValueError):
    pass
        
class FlapsStatusDisplay(QWidget):
    """Anzeige aller Klappen-Zustände mit Hervorhebung des aktuellen."""
    def __init__(self, states:list[FlapState]=[]): #["Kampf", "Start", "Landung"]):
        super().__init__()
        self.states = []
        self.labels = []
        self.current_state = FlapState.NONE
        self._layout = QVBoxLayout(self)
        self.set_states(states)

    def set_states(self, states:list[FlapState]):
        """Baut die Labels für die übergebenen Flap-States neu auf.

        Wird aufgerufen, sobald ein (neues) Flugzeug bekannt ist, da erst
        dann feststeht, welche Klappen-Stufen es überhaupt gibt.
        """
        for lbl in self.labels:
            self._layout.removeWidget(lbl)
            lbl.deleteLater()
        self.labels = []
        self.states = states
        self.current_state = FlapState.NONE

        for state in states:
            lbl = SelectableLabel(state.value, FlapStateDisplayText[state.value])
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            lbl.setStyleSheet("color: gray")
            self._layout.addWidget(lbl)
            self.labels.append(lbl)

    def set_state(self, new_state: FlapState, new_aim_state: FlapState | None): # TODO: Implement usage of Aim Level
        self.current_state = new_state
        
        for lbl in self.labels:
            if lbl.id == new_state.value:
                lbl.activate()
                # lbl.setStyleSheet("color: green; font-weight: bold")
            else:
                lbl.deactivate()
                # lbl.setStyleSheet("color: gray; font-weight: normal")
                
    def set_safe_level(self, level:FlapState):
        """Set the highest Flap state which is usable safely.
        
        Args:
            level(FlapState): Highest safe Flap state
        
        Raises:
            ValueError: If given Level is not Valid
            FlapValueException: If the current Plane does not have this type of Flaps
        """
        
        if not isinstance(level, FlapState):
            raise ValueError(f"{level} is not a valid Flap State.")
        if level == FlapState.NONE:
            for lbl in self.labels:
                lbl.mark_unsafe()
            return
        if level not in self.states:
            raise FlapValueException(f"This plane has no {level} Flaps.")
        
        safe_level_index = self.states.index(level)
        for i, lbl in enumerate(self.labels):
            if i <= safe_level_index:
                lbl.mark_safe()
            else:
                lbl.mark_unsafe()

class MechanicalState(Enum):
    RETRACTED = 0
    MOVING = 1
    DEPLOYED = 2        

class AircraftStatusDock(QDockWidget):
    """AircraftStatus Dock Widget to be used in the main Window if activated"""
    _main_layout: QHBoxLayout
    
    
    __lamps: dict[str, Lamp]
    __mech_box: QGroupBox
    
    
    def __init__(self, title="Aircraft Status"):
        super().__init__(title)
        self.setObjectName(title)
        self.__lamps = {}
        
        self.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)

        main_widget = QWidget()
        self._main_layout = QHBoxLayout(main_widget)
        
        self.__lamps["landing_gear"] = Lamp("Fahrwerk")
        self.__lamps["brake_flaps"] = Lamp("Bremsklappen")
        self.__lamps["flaps"] = Lamp("Klappen")
        
        mech_layout = QHBoxLayout()
        mech_layout.addWidget(self.__lamps["landing_gear"])
        mech_layout.addWidget(self.__lamps["brake_flaps"])
        mech_layout.addWidget(self.__lamps["flaps"])
        
        self.__mech_box = QGroupBox("Mechanische Systeme")
        self.__mech_box.setLayout(mech_layout)
        self._main_layout.addWidget(self.__mech_box)
        
        self.__flap_status_box = QGroupBox("Klappen")
        flap_layout = QHBoxLayout()       
        self.__flap_status_box.setLayout(flap_layout)
        self._flap_status_information = FlapsStatusDisplay()
        flap_layout.addWidget(self._flap_status_information)
        self._main_layout.addWidget(self.__flap_status_box)
        
        self.setWidget(main_widget)
        
        HistoryLength = 10
        
        self.__gear_hist = ValueHistory(HistoryLength)
        self.__flap_hist = ValueHistory(HistoryLength)
        self.__breaking_flap_hist = ValueHistory(HistoryLength)
        
        self.__has_airbrake = True
    
    @Slot(str)
    def on_no_plane(self, message:str):
        for lamp in self.__lamps.values():
            lamp.set_state(LampState.OFF)
        self._flap_status_information.set_states([])
        self._flap_status_information.set_state(FlapState.NONE, FlapState.NONE)
        self._flap_status_information.set_safe_level(FlapState.NONE)

    @Slot(Plane)
    def on_new_plane(self, updated_plane:Plane):
        self.__has_airbrake = updated_plane.telemetry.airbrake is not None
        # FlapState.NONE hat keinen Eintrag in FlapStateDisplayText und wird
        # nicht als eigenes, wählbares Klappen-Label angezeigt.
        possible_states = [possible.name for possible in updated_plane.flaps.possible
                            if possible.name != FlapState.NONE]
        self._flap_status_information.set_states(possible_states)
        
        self.__lamps["brake_flaps"].setVisible(self.__has_airbrake) # hide Airbrake Lamp if plane has none
        
        self.on_new_telemetry(updated_plane)

    @Slot(Plane)
    def on_new_telemetry(self, updated_plane:Plane):
        new_telemetry = updated_plane.telemetry
        
        current_flap_aim = self.__get_flap_state_by_deployed_perc(updated_plane, new_telemetry.flaps.aim) if new_telemetry.flaps.aim is not None else None
        current_flap_state = self.__get_flap_state_by_deployed_perc(updated_plane, new_telemetry.flaps.current)
        
        safe_flap_state = FlapState.NONE
        current_flap_speed_limits = updated_plane.properties.speed_limits
        
        ias = new_telemetry.ias
        
        if current_flap_speed_limits.landing_flap is not None and ias <= current_flap_speed_limits.landing_flap:
            safe_flap_state = FlapState.LANDING
        elif current_flap_speed_limits.start_flap is not None and ias <= current_flap_speed_limits.start_flap:
            safe_flap_state = FlapState.START
        elif current_flap_speed_limits.combat_flap is not None and ias <= current_flap_speed_limits.combat_flap:
            safe_flap_state = FlapState.COMBAT
            
        self._flap_status_information.set_safe_level(safe_flap_state)
        self._flap_status_information.set_state(current_flap_state, current_flap_aim)
        
        self.__gear_hist.add(new_telemetry.gear)
        
        self.__flap_hist.add(new_telemetry.flaps.current)
        
        if new_telemetry.airbrake is not None:
            self.__breaking_flap_hist.add(new_telemetry.airbrake)

        if self.__gear_hist.current > 0:
            if self.__gear_hist.is_accelerating or self.__gear_hist.is_decelerating:
                self.__lamps["landing_gear"].set_state(LampState.BLINKING)
            else:
                self.__lamps["landing_gear"].set_state(LampState.ON)
        else: 
            self.__lamps["landing_gear"].set_state(LampState.OFF)
            
        if self.__flap_hist.current > 0:
            if self.__flap_hist.is_accelerating or self.__flap_hist.is_decelerating:
                self.__lamps["flaps"].set_state(LampState.BLINKING)
            else:
                self.__lamps["flaps"].set_state(LampState.ON)
        else: 
            self.__lamps["flaps"].set_state(LampState.OFF)
                    
        if new_telemetry.airbrake is not None and self.__has_airbrake:
            if self.__breaking_flap_hist.current > 0:
                if self.__breaking_flap_hist.is_accelerating or self.__breaking_flap_hist.is_decelerating:
                    self.__lamps["brake_flaps"].set_state(LampState.BLINKING)
                else:
                    self.__lamps["brake_flaps"].set_state(LampState.ON)
            else:
                self.__lamps["brake_flaps"].set_state(LampState.OFF)
        
    
    @staticmethod
    def __get_flap_state_by_deployed_perc(plane:Plane, perc:float) -> FlapState:
        for state in plane.flaps.possible:
            if perc <= state.min_perc:
                return state.name
        
        return FlapState.NONE
    