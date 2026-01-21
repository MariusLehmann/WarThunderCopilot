from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QTabWidget, QPushButton, QWidget, QMessageBox,
                               QLineEdit, QLabel, QComboBox, QFormLayout)
from PySide6.QtCore import Signal, Qt
from backend.settings import GlobalSettings, GeneralSettings, WarningSettings
from Packages.local_db import LocalDB
from Packages.settings_collection import SettingsCollection
from .warning_settings import WarningSettingsTab
from .general_settings import GeneralSettingsTab
from .sound_settings import SoundSettingsTab
from paths import USER_DIR
import os
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QPushButton
import subprocess

def create_open_user_dir_button(parent=None):
    """Factory: returns a QPushButton that opens USER_DIR when clicked."""
    btn = QPushButton(parent)
    btn.setToolTip("App-Ordner öffnen")
    btn.setText("")  # Leertext, nur Icon anzeigen (oder "Ordner öffnen" setzen)
    icon = QIcon.fromTheme("folder-open")
    if not icon.isNull():
        btn.setIcon(icon)

    def _open_user_dir():
        # Versuche mit QDesktopServices, fallback auf plattformspezifische Aufrufe
        url = QUrl.fromLocalFile(USER_DIR)
        if not QDesktopServices.openUrl(url):
            if os.name == "nt":
                os.startfile(USER_DIR)
            elif os.name == "posix":
                subprocess.Popen(["xdg-open", USER_DIR])
            else:
                raise RuntimeError(f"Cannot open folder: {USER_DIR}")

    btn.clicked.connect(_open_user_dir)
    return btn
class SettingsWindow(QDialog):
    """Settings window with tabbed interface for different settings groups."""
    _changes_detected: bool = False
    _original_settings: GlobalSettings
    _settings_obj: GlobalSettings
    
    # Signals
    general_settings_changed = Signal(GeneralSettings)
    warning_settings_changed = Signal(WarningSettings)
    sound_settings_changed = Signal()  # TODO: SoundSettings mit übergeben
    settings_saved = Signal(object)  # Signal wird mit Settings-Objekt emittiert
    
    
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setModal(True)
        self.resize(600, 400)
        
        # Original Settings für Änderungserkennung
        if isinstance(settings, GlobalSettings):
            self._original_settings = settings
        elif isinstance(settings, SettingsCollection):
            self._original_settings = GlobalSettings.from_settingsCollection(settings)
        else:
            raise ValueError("Ungültiger Typ für Einstellungen")
        
        self._init_ui()
        self._load_settings()
        
    def _load_settings(self):
        """Lädt gespeicherte Einstellungen in die UI-Elemente.
        """
        db = LocalDB()
        self._settings_obj = GlobalSettings.from_dict(db.get_global_settings())
        
        self.general_tab.load_settings(self._settings_obj.general)
        self.warnings_tab.load_settings(self._settings_obj.warning)

        return
    
    def _save_settings(self):
        """Speichert die aktuellen Einstellungen aus der UI-Elemente.
        """
        db = LocalDB()
        
        self._collect_settings()
        db.save_global_settings(self._settings_obj.to_dict())    
        self._original_settings = self._settings_obj
        self._changes_detected = False

        if self.sounds_tab.has_changes():
            self.sounds_tab.save_changes()
        return
            
    def _init_ui(self):
        """Initialisiert die Benutzeroberfläche."""
        layout = QVBoxLayout()
        
        self.inputs = {}
        # Tab Widget erstellen
        self.tab_widget = QTabWidget()
        
        # General Tab
        self.general_tab = GeneralSettingsTab()
        self.tab_widget.addTab(self.general_tab, "General")
        
        # Warnings Tab
        self.warnings_tab = WarningSettingsTab()
        self.tab_widget.addTab(self.warnings_tab, "Warnings")
        
        # Sounds Tab
        self.sounds_tab = SoundSettingsTab()
        self.tab_widget.addTab(self.sounds_tab, "Sounds")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons am unteren Rand
        button_layout = QHBoxLayout()
        self.user_dir_button = create_open_user_dir_button(self)
        button_layout.addWidget(self.user_dir_button)
        button_layout.addStretch()
        
        # Abbrechen Button
        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_button)
        
        # Reset Button
        self.reset_button = QPushButton("Zurücksetzen")
        self.reset_button.clicked.connect(self._on_reset)
        button_layout.addWidget(self.reset_button)
        
        # Speichern Button
        self.save_button = QPushButton("Speichern")
        self.save_button.clicked.connect(self._on_save)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_reset(self):
        """Setzt alle Einstellungen auf Standardwerte zurück.
        """
        self._load_settings()
        
    def _on_save(self):
        """Wird aufgerufen, wenn der Speichern-Button geklickt wird."""
        self._check_for_changes_and_send_signals()
        self._save_settings()
        
        self.settings_saved.emit(self._settings_obj)
        self.accept()  # Schließt das Fenster mit Accept-Status
    
    def _collect_settings(self) -> GlobalSettings:
        """Sammelt alle Einstellungen und gibt ein Settings-Objekt zurück.
        
        Diese Methode sollte später implementiert werden, um alle
        Einstellungen aus den Tabs zu sammeln.
        """
        settings = GlobalSettings(
            general=self.general_tab.get_settings(),
            warning=self.warnings_tab.get_settings(),
            # sound=None  # TODO: Sound settings in den RAM kopieren
        )
        self._settings_obj = settings
        return settings
    
    def _changes_present(self) -> bool:
        """Prüft, ob es ungespeicherte Änderungen gibt.
        
        Returns:
            True wenn es Änderungen gibt, sonst False
        """
        if self._changes_detected:
            return True
        else:
            return self._original_settings != self._collect_settings() or self.sounds_tab.has_changes()
    
    def _check_for_changes_and_send_signals(self):
        """Prüft auf Änderungen und sendet ggf. Signale.
        
        :returns: True wenn Änderungen vorhanden sind, sonst False
        :rtype: bool
        """
        if self._changes_present():
            if self._original_settings.general != self._settings_obj.general:
                self.general_settings_changed.emit(self._settings_obj.general)
            
            if self._original_settings.warning != self._settings_obj.warning:
                self.warning_settings_changed.emit(self._settings_obj.warning)
            
            if self.sounds_tab.has_changes():
                self.sound_settings_changed.emit()
            return True
        return False
    
    def closeEvent(self, event):
        """Wird aufgerufen, wenn das Fenster geschlossen wird.
        
        Prüft auf ungespeicherte Änderungen und fragt ggf. nach.
        """
        if self._changes_present():
            reply = QMessageBox.question(
                self,
                "Ungespeicherte Änderungen",
                "Es gibt ungespeicherte Änderungen. Möchten Sie diese speichern?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:  # Cancel
                event.ignore()
        else:
            event.accept()


