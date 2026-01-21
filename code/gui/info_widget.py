from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
import darkdetect


class InfoDockWidget(QDockWidget):
    def __init__(self, parent, title="Plane Information"):
        super().__init__(title)
        self.setObjectName(title)  # wichtig für saveState/restoreState
        self.parent_window = parent
        self.info_label = QLabel("No Plane Information avaliable yet")
        self.info_label.setWordWrap(True)
        
        
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.info_label)
        widget.setLayout(layout)
        self.setWidget(widget)
        
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)

    def init_window(self):
        if self.parent_window.own_plane.max_values_avaliable:
            
            max_speeds = self.parent_window.own_plane.max_speeds
            plane_type = self.parent_window.own_plane.name

            # Theme aus DB lesen (falls vorhanden) und Textfarbe bestimmen
            text_color = "inherit"
            try:
                theme_choice = self.parent_window.db.get_value("main_config", "theme")
                if theme_choice == "Dunkel":
                    text_color = "#FFFFFF"
                elif theme_choice == "Hell":
                    text_color = "#000000"
                elif theme_choice == "Automatisch":
                    detected = darkdetect.theme().lower()
                    text_color = "#FFFFFF" if detected == "dark" else "#000000"
            except Exception:
                text_color = "inherit"

            # Basis-Fontgröße ermitteln (Fallback 12pt wenn nicht gesetzt) und um 4pt erhöhen
            base_pt = self.info_label.font().pointSize()
            if base_pt <= 0:
                base_pt = 12
            new_pt = base_pt + 4
            font_family = self.info_label.font().family()

            # Tabelle als HTML bauen
            rows = ""
            for key, value in max_speeds.items():
                unit = " km/h"
                if value is None:
                    continue
                if "mach" in key.lower():
                    unit = " M"
                    if value == 999.9:
                        continue
                
                key_cell = f"<td style='padding:6px 10px;border:1px solid #ddd;text-align:left;color:{text_color}'>{key.capitalize()}</td>"
                val_cell = f"<td style='padding:6px 10px;border:1px solid #ddd;text-align:right;color:{text_color}'>{value}{unit}</td>"
                rows += f"<tr>{key_cell}{val_cell}</tr>"

            if rows == "":
                table_html = f"<div style='margin-top:6px;color:{text_color}'>Keine Geschwindigkeitsdaten verfügbar</div>"
            else:
                table_html = f"""
                <table style='border-collapse:collapse;margin-top:6px;border:1px solid #ddd;color:{text_color}'>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                """

            # Gesamtes HTML mit vergrößerter Schrift und fettem "Max Speeds"
            html = f"""
            <div style='font-size:{new_pt}pt; font-family:\"{font_family}\"; color:{text_color};'>
                <div style='font-weight:bold; margin-bottom:6px;'>{plane_type}</div>
                <div style='font-weight:bold; margin-top:8px;'>Max Speeds:</div>
                {table_html}
            </div>
            """

            self.info_label.setTextFormat(Qt.RichText)
            self.info_label.setText(html)
        else:
            self.info_label.setText(f"This plane is not known to the Database, pleas add information for planetype {self.parent_window.own_plane.planetype}")



