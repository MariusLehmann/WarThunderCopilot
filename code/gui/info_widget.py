from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Slot

from Models import Plane, Theme
from wt_dataclasses import SpeedLimit

import darkdetect


class InfoDockWidget(QDockWidget):
    _plane_name: str | None
    _plane_speed_limits: list[tuple[str, SpeedLimit|int|None]] | None
    
    _theme: Theme
    
    def __init__(self, theme:Theme, title="Plane Information"):
        super().__init__(title)
        self.setObjectName(title)  # wichtig für saveState/restoreState
        self.info_label = QLabel("No Plane Information avaliable yet")
        self.info_label.setWordWrap(True)
        
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.info_label)
        widget.setLayout(layout)
        self.setWidget(widget)
        
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
        self._theme = theme

    def __reload_info_label(self):
        plane_type = self._plane_name
        max_speeds = self._plane_speed_limits
        
        if plane_type is not None and max_speeds is not None:
            # get and use Theme
            text_color = "inherit"
            try:
                if self._theme == Theme.DARK:
                    text_color = "#FFFFFF"
                elif self._theme == Theme.LIGHT:
                    text_color = "#000000"
                elif self._theme == Theme.AUTO:
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
            for key, value in max_speeds:
                unit = " M" if "mach" in key.lower() else " km/h"
                
                if isinstance(value, (int, float)):
                    if value is None:
                        continue
                    val = str(value)
                elif isinstance(value, SpeedLimit):
                    if value is None:
                        continue
                    if value.min_speed == value.max_speed:
                        val = str(value.min_speed)
                    else:
                        val = f"{value.min_speed} - {value.max_speed}"
                else:
                    continue
                
                key_cell = f"<td style='padding:6px 10px;border:1px solid #ddd;text-align:left;color:{text_color}'>{key.capitalize()}</td>"
                val_cell = f"<td style='padding:6px 10px;border:1px solid #ddd;text-align:right;color:{text_color}'>{val}{unit}</td>"
                
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

            self.info_label.setTextFormat(Qt.TextFormat.RichText)
            self.info_label.setText(html)
        else:
            self.info_label.setText("No Plane Information avaliable yet")
    
    
    @Slot(Plane)
    def on_new_plane(self, plane:Plane):
        self._plane_name = plane.name
        self._plane_speed_limits = plane.properties.speed_limits.get_limit_list()
        
        self.__reload_info_label()
    
    @Slot(str)
    def on_no_plane(self, message):
        info_text = f"This plane is not known to the Database or a fatal error occurred while fetching.\n\nError Message: {message}"
        
        self._plane_name = None
        self._plane_speed_limits = None
        
        self.info_label.setText(info_text)

    @Slot(Theme)
    def on_theme_change(self, theme:Theme):
        self._theme = theme
        
        self.__reload_info_label()
