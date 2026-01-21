from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QAction, QIcon, QActionGroup
from PySide6.QtCore import Qt

import sys
import darkdetect
import qdarktheme
from logging_setup import get_logger

from Models import Theme

from gui.base_elements import BasicDockWidget
from Packages.Models.Plane import WTPlane
from Packages.local_db import LocalDB
from Packages import SettingsCollection

from gui.status_widget import AircraftStatusDock
from gui.info_widget import InfoDockWidget
from gui.main_settings import SettingsWindow

from backend.wtFetcher import WTUpdater
from backend.worker import dataFetcher
from backend.warningEngine import PlaneSpeedWarningEngine
from backend.SoundEngine import Sound, SoundBox

from settings import DEBUG_MODE

# For References 
from backend.settings import GeneralSettings, GlobalSettings

logger = get_logger(__name__, filename='main_window.log')
class ModuleDock(BasicDockWidget):
    def __init__(self, title, content):
        super().__init__(title, content)
    
    def _init_window(self, content:str) -> None:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(content))
        widget.setLayout(layout)
        self.setWidget(widget)
    
    def _update_window(self) -> None:
        pass


class MainWindow(QMainWindow):
    __inhibit_process = None
    __settings:SettingsCollection
    __global_settings:GlobalSettings
    _default_sound_box:SoundBox
    _priority_sound_box:SoundBox
    __current_theme:Theme
    
    def __init__(self, settings:SettingsCollection):
        super().__init__()
        self.__settings = settings # TODO: Think of a way to init without settings given
        
        self.__set_prevent_device_sleep()
        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks | QMainWindow.DockOption.GroupedDragging)
        
        self._default_sound_box = SoundBox(channel_index=0)
        self._priority_sound_box = SoundBox(channel_index=1)
        
        self.db = LocalDB()
        self.__global_settings = GlobalSettings.from_dict(self.db.get_global_settings())
        self.updater = WTUpdater(settings.ip, DEBUG_MODE)
        self.own_plane:WTPlane|None = None
        self.update_interval = settings.intervall
        self.error_intervall = 5000
        self.worker_had_error = False
        
        self.periodic_workers:list[object] = [self._default_sound_box, self._priority_sound_box]
        
        self.setWindowTitle("WTCopilot")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(900, 600)

        central = QLabel(f"War Thunder - Copilot")
        central.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(central)

        self.modules = {
            # "Modul A": ModuleDock("Modul A", "Inhalt von Modul A"),
            "Plane Information": InfoDockWidget(self),
            "Status": AircraftStatusDock("Flugzeug Status", self)
        }
        self.std_pos = {
            # "Modul A": Qt.DockWidgetArea.RightDockWidgetArea,
            "Plane Information": Qt.DockWidgetArea.RightDockWidgetArea,
            "Status": Qt.DockWidgetArea.BottomDockWidgetArea
        }

        # Docks hinzufügen
        for i, (name, dock) in enumerate(self.modules.items()):
            self.addDockWidget(self.std_pos[name], dock)

        # Menü zum Anzeigen/Verstecken
        self.module_menu = self.menuBar().addMenu("Module")
        for name, dock in self.modules.items():
            action = QAction(name, self, checkable=True, checked=True)
            action.triggered.connect(lambda checked, d=dock: d.setVisible(checked))
            dock.visibilityChanged.connect(lambda visible, a=action: a.setChecked(visible))
            self.module_menu.addAction(action)

        # Theme-Umschalter
        self.__init_theme_menu()
        # Einstellungen-Menü
        
        self.settings_action = QAction("Einstellungen", self)
        self.settings_action.triggered.connect(self._open_settings_window)
        self.menuBar().addAction(self.settings_action)

        # Layout wiederherstellen
        saved_layout = self.db.get_layout()
        if saved_layout:
            self.restoreState(saved_layout)
            
        # Setup backend Worker
        self.init_worker(settings.ip, DEBUG_MODE, self.update_interval, self.error_intervall)
        # Setup warning module
        self.init_warning_modules()
        
        self.connect_signals()


    def init_worker(self, endpoint_ip:str, debug_mode:bool = False, std_intervall:int = 100, std_error_intervall:int = 5000) -> None:
        """Create an Backend Worker to Fetch Data from the local Game API in another Thread. 
            The worker running intervall is controlled by self.update_interval.
            
            If the Worker encounters an error, the Update intervall is reduced to self.error_intervall.
        
            :param endpoint_ip: The Address of the local Warthunder web endpoint
            :type endpoint_ip: str
            :param debug_mode: If True, data is fetched from a local File instad of the Web Endpoint, defaults to False
            :type debug_mode: bool, optional 
            :param std_intervall: The intervall of running the worker in normal operation in ms, defaults to 100
            :type std_intervall: int, optional
            :param std_error_intervall: The intervall of running the worker in case of an error in ms, defaults to 5000
            :type std_error_intervall: int, optional
        """
        self.fetcher_worker = dataFetcher(endpoint_ip, debug_mode, std_intervall, std_error_intervall)
        self.fetcher_worker.new_plane_data.connect(self.__update_plane)
        self.periodic_workers.append(self.fetcher_worker)
        
        
    def init_warning_modules(self):
        """init modules for calculating warnings and allerts"""
        self._plane_speed_warning_e = PlaneSpeedWarningEngine(
            speed_warning_treshold=self.__global_settings.warning.speed_treshold,
            min_diff=self.__global_settings.warning.min_diff,
            max_diff=self.__global_settings.warning.max_diff,
            mach_speed_threshold=self.__global_settings.warning.mach_threshold,
            mach_min_diff=self.__global_settings.warning.min_mach_diff,
            mach_max_diff=self.__global_settings.warning.max_mach_diff
        )
           
    def connect_signals(self):
        """Connect Signals and Slots between GUI and Backend Workers."""
        self.fetcher_worker.new_plane_data.connect(self._plane_speed_warning_e.on_new_plane)
        self.fetcher_worker.new_telemetry_data.connect(self._plane_speed_warning_e.on_new_telemetry)   
        
        self._plane_speed_warning_e.play_sound_signal.connect(self.play_sounds)
        self._plane_speed_warning_e.stop_sound_signal.connect(self.stop_sounds)
        
    def __update_plane(self, plane:WTPlane)-> None:
        """Update the Plane for Which informations are displayed

        :param plane: the New Plane Object
        :type plane: WTPlane
        """
        # TODO: Remove While Implementing everything with Signals
        self.own_plane = plane
        self.reload_windows()
        
    def play_sounds(self, sounds:list[Sound]|Sound) -> None:
        if isinstance(sounds, Sound):
            sounds = [sounds]
        for sound in sounds:
            if sound.priority_playback:
                self._priority_sound_box.add_sound(sound)
            else:
                self._default_sound_box.add_sound(sound)
    
    def stop_sounds(self, sounds:list[Sound]|Sound) -> None:
        if isinstance(sounds, Sound):
            sounds = [sounds]
        for sound in sounds:
            if sound.priority_playback:
                self._priority_sound_box.remove_sound(sound)
            else:
                self._default_sound_box.remove_sound(sound)
        
    def reload_windows(self):
        for name, dock in self.modules.items():
            if hasattr(dock, 'init_window'):
                dock.init_window()
            if hasattr(dock, '_update_window'):
                dock._update_window()
    
    def _open_settings_window(self):
        """Öffnet das Einstellungsfenster."""
        settings_window = SettingsWindow(self, self.__global_settings)
        settings_window.settings_saved.connect(self._on_settings_saved)
        settings_window.general_settings_changed.connect(self._on_general_settings_change)
        settings_window.warning_settings_changed.connect(self._plane_speed_warning_e.on_new_threshold_settings)
        
        self._pause_all_workers()
        settings_window.exec()
        self._resume_all_workers()
    
    def _on_settings_saved(self, settings):
        """Update the settings reference in the Window after settings where saved.
        
        
        :param settings: New GlobalSettings Oject
        """
        self.__global_settings = settings
    
    def _pause_all_workers(self):
        """Pause all periodic workers or tasks found to self.periodic_workers
        """
        for worker in self.periodic_workers:
            if hasattr(worker,'pause'):
                worker.pause()
    
    def _resume_all_workers(self):
        for worker in self.periodic_workers:
            if hasattr(worker,'resume'):
                worker.resume()        

    def closeEvent(self, event):
        self.fetcher_worker.stop()
        self._default_sound_box.stop(wait=True)
        self._priority_sound_box.stop(wait=True)
        self.__revoke_prevent_device_sleep()
            
        self.db.save_layout(self.saveState())
        event.accept()
        
    def __set_prevent_device_sleep(self):
        """Tell the System not to turn off the Display or device because the App is active and has Priority."""
        if sys.platform == 'win32':
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        elif sys.plattform.startswith('linux'):
            import subprocess
            if os.system("command -v systemd-inhibit > /dev/null") == 0:
                try:
                    self.__inhibit_process = subprocess.Popen(
                        ["systemd-inhibit", "--what=idle:sleep", "why=WTCopilot is running", "sleep", "infinity"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    print(f"Failed to activate Sleep Lock: {e}")
            
    def __revoke_prevent_device_sleep(self):
        """Tell the system it is allowed to turn off the Display and Device automatically again."""
        if sys.platform == 'win32':
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        elif sys.plattform.startswith('linux'):
            import subprocess
            if self.__inhibit_process:
                try:
                    self.__inhibit_process.terminate()
                    self.__inhibit_process.wait()
                    self.__inhibit_process = None
                except Exception as e:
                    print(f"Failed to deactivate Sleep Lock: {e}")
                    
    def _on_general_settings_change(self, new_settings:GeneralSettings):
        """Wird aufgerufen, wenn die allgemeinen Einstellungen geändert wurden.
        
        :param new_settings: Die neuen allgemeinen Einstellungen
        """
        if self.__global_settings.general.ip != new_settings.ip:
            logger.info("IP-Adresse geändert, Worker wird neu gestartet.")
            self.periodic_workers.remove(self.fetcher_worker)
            self.fetcher_worker.stop()
            self.init_worker(new_settings.ip, DEBUG_MODE, self.update_interval, self.error_intervall)
            
        if self.__global_settings.general.intervall != new_settings.intervall or \
            self.update_interval != new_settings.intervall:
                logger.info("Update Intervall geändert, Worker Intervall wird angepasst.")
                self.update_interval = new_settings.intervall
                self.fetcher_worker.update_intervall(self.update_interval)
        
        if self.__current_theme != new_settings.theme:
            self.__set_theme(new_settings.theme)
        
        
    def __set_theme(self, theme:Theme) -> None:
        """Set the theme of the application.

        Args:
            theme (Theme): The theme to set.
        """
        assert isinstance(theme, Theme) or theme in Theme
        if isinstance(theme, int):
            theme = Theme(theme)
        
        
        self.__current_theme = theme
        
        match theme:
            case Theme.AUTO:
                self.theme_auto.setChecked(True)
                theme_str = str(darkdetect.theme()).lower()
                qdarktheme.setup_theme(theme_str)
            case Theme.LIGHT:
                self.theme_light.setChecked(True)
                qdarktheme.setup_theme("light")
            case Theme.DARK:
                self.theme_dark.setChecked(True)
                qdarktheme.setup_theme("dark")
    
    def __init_theme_menu(self):
        """Initialize the theme menu in the menu bar."""
        self.theme_menu = self.menuBar().addMenu("Theme")
        self.theme_auto = QAction("Automatisch (System)", self, checkable=True)
        self.theme_light = QAction("Hell", self, checkable=True)
        self.theme_dark = QAction("Dunkel", self, checkable=True)
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        
        for action in [self.theme_auto, self.theme_light, self.theme_dark]:
            self.theme_menu.addAction(action)
            self.theme_action_group.addAction(action)

        self.theme_auto.triggered.connect(lambda: self.__set_theme(Theme.AUTO))
        self.theme_light.triggered.connect(lambda: self.__set_theme(Theme.LIGHT))
        self.theme_dark.triggered.connect(lambda: self.__set_theme(Theme.DARK))

        self.__set_theme(self.__global_settings.general.theme)
        
        
            