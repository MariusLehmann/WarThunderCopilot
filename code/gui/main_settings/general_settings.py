from .basics import SettingsTab
from backend.settings import GeneralSettings
from PySide6.QtWidgets import QLabel, QLineEdit, QComboBox, QFormLayout
from Models import THEME_NAMES

class GeneralSettingsTab(SettingsTab):
    """Einstellungen Tab für allgemeine Einstellungen."""
    
    def _init_ui(self):
        """Initialisiert die Benutzeroberfläche des Tabs."""
        
        form_layout = QFormLayout()
        
        self.inputs["ip"] = QLineEdit()
        self.inputs["intervall"] = QLineEdit()
        self.inputs["theme"] = QComboBox()
        self.inputs["theme"].addItems(list(THEME_NAMES.values()))
        
        form_layout.addRow(QLabel("IP Adresse:"), self.inputs["ip"])
        form_layout.addRow(QLabel("Update Intervall (ms):"), self.inputs["intervall"])
        form_layout.addRow(QLabel("Theme:"), self.inputs["theme"])
        
        self.main_layout.addLayout(form_layout)
    
    def load_settings(self, settings:GeneralSettings):
        """Lädt die Einstellungen in die UI-Elemente.
        
        Args:
            settings (GeneralSettings): Das Settings-Objekt mit den aktuellen Einstellungen.
        """
        self.inputs["ip"].setText(settings.ip)
        self.inputs["intervall"].setText(str(settings.intervall))
        self.inputs["theme"].setCurrentText(THEME_NAMES[settings.theme])
    
    def get_settings(self) -> GeneralSettings:
        """Sammelt die Einstellungen aus den UI-Elementen.
        
        Returns:
            GeneralSettings: Ein Objekt mit den gesammelten Einstellungen.
        """
        rev_theme_names = {v: k for k, v in THEME_NAMES.items()}
        general_settings = GeneralSettings(
            ip=self.inputs["ip"].text(),
            intervall=int(self.inputs["intervall"].text()),
            theme=rev_theme_names[self.inputs["theme"].currentText()]
        )
        
        return general_settings

