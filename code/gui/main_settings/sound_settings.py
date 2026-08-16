from .basics import SettingsTab
from PySide6.QtWidgets import (
    QLabel,
    QComboBox,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QSlider,
    QFileDialog,
)
from PySide6.QtCore import Qt
from pathlib import Path
import shutil

from backend.settings import SoundSettings, SoundProperties
from backend.SoundEngine import SoundEngine, WT_Sound, get_default_sound_properties
from paths import SOUNDS_DIR, USER_SOUNDS_DIR


class SoundSettingsTab(SettingsTab):
    """Einstellungen Tab für Sound Einstellungen.

    Für jeden in backend/SoundEngine.py definierten WT_Sound-Eintrag wird eine
    Zeile mit: Name, Datei-Auswahl, Upload-Button, Lautstärke-Slider und
    Play-Button erstellt.
    """

    def _init_ui(self):
        self._has_changes = False
        self._master_volume = 1.0
        # Arbeitskopie der Sound-Properties, per Identifier. Wird in
        # load_settings() mit gespeicherten Werten überschrieben und in
        # get_settings() zurückgegeben.
        self._properties: dict[str, SoundProperties] = {
            sound.value.identifier: get_default_sound_properties(sound.value.identifier)
            for sound in WT_Sound
        }
        # Eigene SoundEngine nur für die Vorschau-Play-Buttons dieses Tabs.
        self._preview_engine = SoundEngine()
        self._widgets: dict = {}

        # Master volume row
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Master Volume:"))
        self._master_slider = QSlider(Qt.Orientation.Horizontal)
        self._master_slider.setRange(0, 100)
        self._master_slider.setValue(int(self._master_volume * 100))
        self._master_val_label = QLabel(f"{int(self._master_volume * 100)}%")

        def on_master_changed(val):
            self._master_val_label.setText(f"{val}%")
            self._master_volume = float(val) / 100.0
            self._has_changes = True

        self._master_slider.valueChanged.connect(on_master_changed)
        top_layout.addWidget(self._master_slider)
        top_layout.addWidget(self._master_val_label)
        self.main_layout.addLayout(top_layout)

        # Grid layout for aligned columns
        grid = QGridLayout()
        headers = ["Name", "File", "Upload", "Volume", "", "Play"]
        for c, h in enumerate(headers):
            grid.addWidget(QLabel(f"<b>{h}</b>"), 0, c)

        known_sound_files = sorted(
            list(Path(SOUNDS_DIR).glob("*.wav")) + list(Path(USER_SOUNDS_DIR).glob("*.wav"))
        )

        row = 1
        for sound in WT_Sound:
            identifier = sound.value.identifier
            properties = self._properties[identifier]

            label = QLabel(sound.value.name)
            label.setToolTip(sound.value.description or "")
            grid.addWidget(label, row, 0)

            combo = QComboBox()
            seen = set()
            for p in known_sound_files:
                key = str(p)
                if key in seen:
                    continue
                seen.add(key)
                combo.addItem(p.name, key)

            idx = next((i for i in range(combo.count()) if combo.itemData(i) == str(properties.file_path)), -1)
            if idx >= 0:
                combo.setCurrentIndex(idx)

            def on_combo_changed(idx, ident=identifier, cmb=combo):
                path = cmb.itemData(idx)
                if path:
                    self._properties[ident].file_path = path
                    self._has_changes = True

            combo.currentIndexChanged.connect(on_combo_changed)
            grid.addWidget(combo, row, 1)

            upload_btn = QPushButton("Upload")

            def on_upload(ident=identifier, cmb=combo):
                files, _ = QFileDialog.getOpenFileNames(self, "Wav Dateien auswählen", str(Path.home()), "WAV Files (*.wav)")
                if not files:
                    return
                for f in files:
                    src = Path(f)
                    dst = Path(USER_SOUNDS_DIR) / src.name
                    try:
                        shutil.copy2(src, dst)
                    except Exception:
                        try:
                            dst.write_bytes(src.read_bytes())
                        except Exception:
                            continue
                    key = str(dst)
                    if next((i for i in range(cmb.count()) if cmb.itemData(i) == key), None) is None:
                        cmb.addItem(dst.name, key)
                    idx = next((i for i in range(cmb.count()) if cmb.itemData(i) == key), -1)
                    if idx >= 0:
                        cmb.setCurrentIndex(idx)
                    self._properties[ident].file_path = key
                self._has_changes = True

            upload_btn.clicked.connect(on_upload)
            grid.addWidget(upload_btn, row, 2)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(properties.volume * 100))
            grid.addWidget(slider, row, 3)

            vol_label = QLabel(f"{int(properties.volume * 100)}%")
            grid.addWidget(vol_label, row, 4)

            def on_slider_changed(val, ident=identifier, lbl=vol_label):
                lbl.setText(f"{val}%")
                self._properties[ident].volume = float(val) / 100.0
                self._has_changes = True

            slider.valueChanged.connect(on_slider_changed)

            play_btn = QPushButton("▶")
            play_btn.clicked.connect(lambda checked=False, s=sound: self._play_preview(s))
            grid.addWidget(play_btn, row, 5)

            self._widgets[identifier] = {
                "label": label,
                "combo": combo,
                "upload": upload_btn,
                "slider": slider,
                "vol_label": vol_label,
                "play": play_btn,
            }

            row += 1

        self.main_layout.addLayout(grid)

    def _play_preview(self, sound: WT_Sound):
        """Spielt einen Sound mit dem aktuellen (ggf. noch ungespeicherten) UI-Stand ab.

        Die Preview-Engine liest ihre Lautstärke/Datei-Zuordnung sonst nur aus den beim
        Erzeugen geladenen Sound-Settings; ohne diesen Sync würde der Play-Button also
        die zuletzt gespeicherten statt der gerade im Slider eingestellten Werte hören lassen.
        """
        self._preview_engine.on_new_sound_settings(self.get_settings())
        self._preview_engine.play_sound(sound, immediate=True)

    def load_settings(self, settings: SoundSettings):
        """Übernimmt gespeicherte Sound-Einstellungen in die UI-Elemente."""
        self._master_volume = settings.master_volume
        self._master_slider.setValue(int(self._master_volume * 100))
        self._master_val_label.setText(f"{int(self._master_volume * 100)}%")

        for identifier, default_properties in self._properties.items():
            properties = settings.sounds.get(identifier, default_properties)
            self._properties[identifier] = properties

            widgets = self._widgets[identifier]
            combo = widgets["combo"]
            idx = next((i for i in range(combo.count()) if combo.itemData(i) == str(properties.file_path)), -1)
            if idx >= 0:
                combo.setCurrentIndex(idx)

            vol_percent = int(properties.volume * 100)
            widgets["slider"].setValue(vol_percent)
            widgets["vol_label"].setText(f"{vol_percent}%")

        self._has_changes = False

    def has_changes(self) -> bool:
        return self._has_changes

    def save_changes(self):
        """Wird nach dem Speichern der Einstellungen aufgerufen (Änderungsflag zurücksetzen).

        Die eigentliche Persistierung läuft über get_settings() ->
        GlobalSettings.to_dict(), hier ist nichts weiter zu tun.
        """
        self._has_changes = False

    def get_settings(self) -> SoundSettings:
        """Gibt die aktuellen Sound-Einstellungen als SoundSettings zurück."""
        return SoundSettings(
            master_volume=self._master_volume,
            sounds=dict(self._properties),
        )
