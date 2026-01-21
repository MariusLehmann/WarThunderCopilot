from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout

class SettingsTab(QWidget):
    """Basisklasse für einzelne Settings Tabs."""
    inputs: dict = {}
    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        
        self._init_ui()
    
    
    def _init_ui(self):
        """Initialisiert die Benutzeroberfläche des Tabs."""
        raise NotImplementedError("Methode _init_ui() muss in der Unterklasse implementiert werden.")
    
    def load_settings(self, settings):
        """Lädt die Einstellungen in die UI-Elemente.
        
        Args:
            settings (GlobalSettings): Das Settings-Objekt mit den aktuellen Einstellungen.
        """
        raise NotImplementedError("Methode load_settings() muss in der Unterklasse implementiert werden.")
    
    def get_settings(self):
        """Sammelt die Einstellungen aus den UI-Elementen.
        
        Returns:
            SettingsObject: Ein Objekt mit den gesammelten Einstellungen.
        """
        raise NotImplementedError("Methode get_settings() muss in der Unterklasse implementiert werden.")
    

