from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QGroupBox

from PySide6.QtCore import Qt, QTimer

from gui.base_elements import SelectableLabel, Lamp

from Packages.Models.Plane import WTPlane, TelemetryData

class FlapValueException(ValueError):
    pass
        
class FlapsStatus(QWidget):
    """Anzeige aller Klappen-Zustände mit Hervorhebung des aktuellen."""
    def __init__(self, states=["Kampf", "Start", "Landung"]):
        super().__init__()
        self.states = states
        self.labels = []
        self.current_state = "Keine"
        layout = QVBoxLayout(self)
        for state in states:
            lbl = SelectableLabel(state)
            lbl.setAlignment(Qt.AlignLeft)
            lbl.setStyleSheet("color: gray")
            layout.addWidget(lbl)
            self.labels.append(lbl)

    def set_state(self, current_state: str):
        self.current_state = current_state
        for lbl in self.labels:
            
            if lbl.name == current_state:
                lbl.activate()
                # lbl.setStyleSheet("color: green; font-weight: bold")
            else:
                lbl.deactivate()
                # lbl.setStyleSheet("color: gray; font-weight: normal")
                
    def set_safe_level(self, level:str):
        """Set the highest Flap state which is usable safely.
        
        Args:
            level(str): Highest safe Flap state, should be one of ["Keine", "Kampf", "Start", "Landung"]
        
        Raises:
            ValueError: If level is not one of ["Keine", "Kampf", "Start", "Landung"]
            FlapValueException: If the current Plane does not have this type of Flaps
        """
        
        if level not in ["Keine", "Kampf", "Start", "Landung"]:
            raise ValueError(f"{level} is not a valid Flap State.")
        if level == "Keine":
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
                

class AircraftStatusDock(QDockWidget):
    """AircraftStatus als eigenes DockWidget, direkt einsatzbereit im MainWindow"""
    def __init__(self, title="Aircraft Status", parent=None):
        super().__init__(title, parent)
        self.mainWindow = parent
        
        self.setObjectName(title)
        # self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)

        # Configure reload Timer
        self.reload_timer = QTimer()
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self.init_window)
        
        # configure update Timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.__update_data)
        
        self.init_window()
    

    def init_window(self):
        if self.mainWindow.own_plane is None:
            print("No Plane found, trying to reload in 1s")
            self.reload_timer.start(1000)
            return
        else:
            self.reload_timer.stop()
            
        # Haupt-Widget im Dock
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)

        # Lampen
        self.landing_gear = Lamp("Fahrwerk")
        self.brake_flaps = Lamp("Bremsklappen")
        
        landing_box = QGroupBox("Landung")
        landing_layout = QHBoxLayout()
        landing_layout.addWidget(self.landing_gear)
        landing_layout.addWidget(self.brake_flaps)
        landing_box.setLayout(landing_layout)
        

        # Klappen-Zustände
        flap_box = QGroupBox("Klappen")
        self.flaps_lamp = Lamp("Klappen")
        
        avaliable_flaps = []
        avaliable_bool = self.mainWindow.own_plane.get_flaps_avaliable()
        for i in range(3):
            if avaliable_bool[i]:
                avaliable_flaps.append(["Kampf", "Start", "Landung"][i])
        
        self.flaps_status = FlapsStatus(avaliable_flaps)
        
        flaps_layout = QHBoxLayout()
        flaps_layout.addWidget(self.flaps_lamp)
        flaps_layout.addWidget(self.flaps_status)
        flap_box.setLayout(flaps_layout)
        
        layout.addWidget(flap_box)
        layout.addWidget(landing_box)
        
        self.setWidget(main_widget)
        
        # start periodic updates
        self.update_timer.start(100)  # alle 0.1 Sekunden

    def update_status(self, landing_gear: bool, brake_flaps: bool, flaps_state: str):
        self.landing_gear.set_state(landing_gear) # TODO Add state blinking for moving parts
        self.brake_flaps.set_state(brake_flaps)
        self.flaps_lamp.set_state(flaps_state != "Keine")
        self.flaps_status.set_state(flaps_state)
        
    def get_status(self):
        return {
            "landing_gear": self.landing_gear.state,
            "brake_flaps": self.brake_flaps.state,
            "flaps_state": self.flaps_lamp.state,
            "flaps_status": self.flaps_status.current_state
        }
        
    def __update_data(self):
        TRANS_DICT = {
            "combat": "Kampf",
            "start": "Start",
            "landing": "Landung",
            "none": "Keine"
        }
        
        tel:TelemetryData = self.mainWindow.own_plane.telemetry
        safe_flap_state = self.mainWindow.own_plane.get_safe_flap_state()
        
        safe_flap_state = TRANS_DICT[safe_flap_state]
        self.flaps_status.set_safe_level(safe_flap_state)
        
        if tel is None or tel == {}:
            return
    
        gear = tel.gear == 100 if tel.gear is not None else False
        flaps_bool = tel.flaps != 0 if tel.flaps is not None else False
        airbrake_bool = tel.airbrake != 0 if tel.airbrake is not None else False
        
        if flaps_bool:
            if tel.flaps <= 25:
                flaps_state = "Kampf"
            elif tel.flaps <= 50:
                flaps_state = "Start"
            else:
                flaps_state = "Landung"
            
        else: 
            flaps_state = "Keine"
            
        self.update_status(gear, airbrake_bool, flaps_state)