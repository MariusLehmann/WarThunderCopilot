from PySide6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QLineEdit, QDialog, QComboBox, QHBoxLayout, QGroupBox
from Packages.local_db import LocalDB
from Packages import SettingsCollection
from paths import SETTINGS_PATH
import ipaddress

def contains_valid_ip(text: str) -> bool:
    """
    Prüft, ob der gegebene String eine gültige IPv4- oder IPv6-Adresse enthält.
    """
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False
    
def is_valid_percentage(text:str) -> bool:
    """ Prüft ob der enthaltene Text eine Gültige Prozentangabe ohne Prozentzeichenn enthällt. """
    try:
        value = float(text)
        if 0 <= value <= 100:
            return True
        else:
            return False
    except ValueError:
        return False


db = LocalDB()
print(f"Settings Path: {SETTINGS_PATH}")
class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WT-Copilot Einstellungen")

        layout = QVBoxLayout(self)
        
        self.ip_input = QLineEdit()
        layout.addWidget(QLabel("IP-Aadresse:"))
        layout.addWidget(self.ip_input)
        
        self.intervall_input = QLineEdit()
        layout.addWidget(QLabel("Update-Intervall [ms]:"))
        layout.addWidget(self.intervall_input)


        self.theme_box = QComboBox()
        
        
        
        
        
        self.theme_box.addItems(["Automatisch", "Hell", "Dunkel"])
        layout.addWidget(QLabel("Theme:"))
        layout.addWidget(self.theme_box)
        
        warning_box = QGroupBox("Warning Settings")
        
        self.speed_treshold_input = QLineEdit()
        self.max_diff_input = QLineEdit()
        self.min_diff_input = QLineEdit()
        
        warning_layout = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        
        warning_box.setLayout(warning_layout)
        warning_layout.addLayout(left_col)
        warning_layout.addLayout(right_col)
    
        
        left_col.addWidget(QLabel("Speed warning Treshold [%]:"))
        right_col.addWidget(self.speed_treshold_input)


        
        min_diff_label = QLabel("Min. Warning Speed Difference [km/h]: ")
        min_diff_label.setToolTip("Minimaler Geschwindigkeitsunterschied, bei dem eine Warnung ausgelöst wird.")
        left_col.addWidget(min_diff_label)
        right_col.addWidget(self.min_diff_input)
        
        max_diff_label = QLabel("Max. Warning Speed Difference [km/h]: ")
        max_diff_label.setToolTip("Maximaler Geschwindigkeitsunterschied, bei dem eine Warnung ausgelöst wird.")
        left_col.addWidget(max_diff_label)
        right_col.addWidget(self.max_diff_input)

        layout.addWidget(warning_box)

        saved = db.get_dict("main_config", default={})
        if saved:
            self.ip_input.setText(saved.get("ip", ""))
            self.intervall_input.setText(str(saved.get("intervall", "")))
            self.theme_box.setCurrentText(saved.get("theme", "Automatisch"))
            
            self.speed_treshold_input.setText(str(saved.get("speed_treshold", "90")))
            self.min_diff_input.setText(str(saved.get("min_diff", "10")))
            self.max_diff_input.setText(str(saved.get("max_diff", "50")))
        else:
            self.intervall_input.setText("500")
            self.speed_treshold_input.setText("90")
            self.min_diff_input.setText("10")
            self.max_diff_input.setText("50")

            

        start_btn = QPushButton("Starten")
        start_btn.clicked.connect(self.check_inputs_and_submit)
        layout.addWidget(start_btn)

    def get_settings(self) -> SettingsCollection:
        """Extract settingsCollection from Settings Window. 
        
        Returns:
            SettingsCollection: This Object contains all selected Settings
        
        """
        ip = self.ip_input.text()
        theme = self.theme_box.currentText()
        intervall = int(self.intervall_input.text()) if self.intervall_input.text() else 1000
        
        speed_warning_treshold = float(self.speed_treshold_input.text())
        
        min_diff_str = self.min_diff_input.text()
        max_diff_str = self.max_diff_input.text()
        
        if "." in min_diff_str:
            min_diff = int(min_diff_str.split(".")[0])
            self.min_diff_input.setText(str(min_diff))
        elif "," in min_diff_str:
            min_diff = int(min_diff_str.split(",")[0])
            self.min_diff_input.setText(str(min_diff))
        else:
            min_diff = int(min_diff_str)
        
        if "." in max_diff_str:
            max_diff = int(max_diff_str.split(".")[0])
            self.max_diff_input.setText(str(max_diff))
        elif "," in max_diff_str:
            max_diff = int(max_diff_str.split(",")[0])
            self.max_diff_input.setText(str(max_diff))
        else:
            max_diff = int(max_diff_str)
        
        
        return SettingsCollection(ip, intervall, theme, speed_warning_treshold, min_diff, max_diff)
        
    def check_inputs_and_submit(self):
        checks = [
            contains_valid_ip(self.ip_input.text()),
            is_valid_percentage(self.speed_treshold_input.text()),
        ]
        if not all(checks):
            raise ValueError("Ungültige Eingabe")
        
        db.save_dict( {**self.get_settings().to_dict()}, "main_config")
        self.save_settings_for_other_widgets()
        self.accept()
        
    def save_settings_for_other_widgets(self):
        db.save_dict({
            "threshold": float(self.speed_treshold_input.text())/100,
            "min_diff": float(self.min_diff_input.text()),
            "max_diff": float(self.max_diff_input.text())
        }, "speed_warning_limits")