from .basics import SettingsTab
from backend.settings import WarningSettings
from PySide6.QtWidgets import QLabel, QLineEdit, QComboBox, QFormLayout, QGroupBox, QVBoxLayout
  
class WarningSettingsTab(SettingsTab):
    """Einstellungen Tab für Warnungs-Einstellungen."""
    def _init_ui(self):
        """Initialisiert die Benutzeroberfläche des Tabs."""
        
        # Speed Warning Settings Group
        speed_group = QGroupBox("Geschwindigkeitswarnungen")
        speed_layout = QFormLayout()
        
        self.inputs["speed_treshold"] = QLineEdit()
        self.inputs["min_diff"] = QLineEdit()
        self.inputs["max_diff"] = QLineEdit()
        
        min_label = QLabel("Min. Warning Speed Difference [km/h]:")
        min_label.setToolTip("Minimaler Geschwindigkeitsunterschied, bei dem eine Warnung ausgelöst wird.")
        max_label = QLabel("Max. Warning Speed Difference [km/h]:")
        max_label.setToolTip("Maximaler Geschwindigkeitsunterschied, bei dem eine Warnung ausgelöst wird.")
        
        speed_layout.addRow(QLabel("Speed Warning Treshold [%]:"), self.inputs["speed_treshold"])
        speed_layout.addRow(min_label, self.inputs["min_diff"])
        speed_layout.addRow(max_label, self.inputs["max_diff"])
        
        speed_group.setLayout(speed_layout)
        
        # Mach Warning Settings Group
        mach_group = QGroupBox("Überschallwarnungen")
        mach_layout = QFormLayout()
        
        self.inputs["mach_threshold"] = QLineEdit()
        self.inputs["min_mach_diff"] = QLineEdit()
        self.inputs["max_mach_diff"] = QLineEdit()
        
        mach_threshold_label = QLabel("Mach Warning Treshold [%]:")
        mach_threshold_label.setToolTip("Schwelle, ab der eine Mach-Warnung ausgelöst wird.")
        min_mach_label = QLabel("Min. Warning Mach Difference:")
        min_mach_label.setToolTip("Minimaler Mach-Unterschied, bei dem eine Warnung ausgelöst wird.")
        max_mach_label = QLabel("Max. Warning Mach Difference:")
        max_mach_label.setToolTip("Maximaler Mach-Unterschied, bei dem eine Warnung ausgelöst wird.")
        
        mach_layout.addRow(mach_threshold_label, self.inputs["mach_threshold"])
        mach_layout.addRow(min_mach_label, self.inputs["min_mach_diff"])
        mach_layout.addRow(max_mach_label, self.inputs["max_mach_diff"])
        
        mach_group.setLayout(mach_layout)
        
        # Add both groups to main layout
        self.main_layout.addWidget(speed_group)
        self.main_layout.addWidget(mach_group)
    
    def load_settings(self, settings:WarningSettings):
        """Lädt die Einstellungen in die UI-Elemente.
        
        Args:
            settings (WarningSettings): Das Settings-Objekt mit den aktuellen Einstellungen.
        """
        self.inputs["speed_treshold"].setText(str(settings.speed_treshold))
        self.inputs["min_diff"].setText(str(settings.min_diff))
        self.inputs["max_diff"].setText(str(settings.max_diff))
        self.inputs["mach_threshold"].setText(str(settings.mach_threshold))
        self.inputs["min_mach_diff"].setText(str(settings.min_mach_diff))
        self.inputs["max_mach_diff"].setText(str(settings.max_mach_diff))
        
    def get_settings(self) -> WarningSettings:
        """Sammelt die Einstellungen aus den UI-Elementen.
        
        Returns:
            WarningSettings: Ein Objekt mit den gesammelten Einstellungen.
        """

        warning_settings = WarningSettings(
            speed_treshold=float(self.inputs["speed_treshold"].text()),
            min_diff=int(self.inputs["min_diff"].text()),
            max_diff=int(self.inputs["max_diff"].text()),
            mach_threshold=float(self.inputs["mach_threshold"].text()),
            min_mach_diff=float(self.inputs["min_mach_diff"].text()),
            max_mach_diff=float(self.inputs["max_mach_diff"].text())
        )
        
        return warning_settings