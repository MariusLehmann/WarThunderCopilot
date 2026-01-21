from .basics import SettingsTab
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QSlider,
    QFileDialog,
)
from PySide6.QtCore import Qt
from pathlib import Path
import shutil
import pygame

from backend.SoundEngine import sounds as sounds_module
from backend.SoundEngine.general import Sound, SoundManager
from backend.SoundEngine.soundBox import SoundBox
from paths import SOUNDS_DIR, USER_SOUNDS_DIR


class SoundSettingsTab(SettingsTab):
    """Einstellungen Tab für Sound Einstellungen.

    Für jede in backend/SoundEngine/sounds.py definierte Sound-Klasse
    wird eine Zeile mit: Name, Datei-Auswahl, Upload-Button, Lautstärke-Slider und Play-Button erstellt.
    """

    def _init_ui(self):
        self._has_changes = False
        self._sound_manager = SoundManager()
        self._sound_box = SoundBox(sound_manager=self._sound_manager)
        # container to keep widgets per sound identifier
        self._widgets: dict = {}

        # Master volume row
        top_layout = QHBoxLayout()
        master_label = QLabel("Master Volume:")
        top_layout.addWidget(master_label)
        master_slider = QSlider(Qt.Orientation.Horizontal)
        master_slider.setRange(0, 100)
        master_slider.setValue(int(self._sound_manager.master_volume * 100))
        master_val_label = QLabel(f"{int(self._sound_manager.master_volume * 100)}%")

        def on_master_changed(val):
            master_val_label.setText(f"{val}%")
            self._sound_manager.change_master_volume(float(val) / 100.0, skip_saving=True)
            self._has_changes = True
            
        master_slider.valueChanged.connect(on_master_changed)
        top_layout.addWidget(master_slider)
        top_layout.addWidget(master_val_label)
        self.main_layout.addLayout(top_layout)

        # Grid layout for aligned columns
        grid = QGridLayout()
        # headers
        headers = ["Name", "File", "Upload", "Volume", "", "Play"]
        for c, h in enumerate(headers):
            grid.addWidget(QLabel(f"<b>{h}</b>"), 0, c)

        # gather sound classes and sort by name
        sound_objs:list[Sound] = []
        for attr_name in dir(sounds_module):
            attr = getattr(sounds_module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Sound):
                try:
                    sound_objs.append(attr())
                except Exception:
                    continue

        sound_objs.sort(key=lambda s: s.name)

        known_sound_files = []
        for p in Path(SOUNDS_DIR).glob("*.wav"):
            known_sound_files.append(Path(p))
        for p in Path(USER_SOUNDS_DIR).glob("*.wav"):
            known_sound_files.append(Path(p))
        known_sound_files = sorted(known_sound_files)
        
        row = 1
        for sound_obj in sound_objs:
            identifier = sound_obj.identifier

            label = QLabel(sound_obj.name)
            # info icon with tooltip showing the sound description
            # info_label = QLabel("|?|")
            label.setToolTip(sound_obj.description or "")
            # info_label.setFixedWidth(20)
            # info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # info_label.setStyleSheet("color: gray;")

            name_container = QHBoxLayout()
            name_container.addWidget(label)
            # name_container.addWidget(info_label)
            name_widget = name_container.parentWidget() if hasattr(name_container, 'parentWidget') else None
            # create a QWidget to host the horizontal layout
            from PySide6.QtWidgets import QWidget
            w = QWidget()
            w.setLayout(name_container)
            grid.addWidget(w, row, 0)

            combo = QComboBox()
            # fill combo with files from buildin and user dirs
            seen = set()
            for p in known_sound_files:
                key = str(p)
                if key in seen:
                    continue
                seen.add(key)
                combo.addItem(p.name, key)

            current = str(self._sound_manager.sound_mapping.get(identifier, sound_obj.standard_path))
            idx = next((i for i in range(combo.count()) if combo.itemData(i) == current), -1)
            if idx >= 0:
                combo.setCurrentIndex(idx)

            def on_combo_changed(idx, ident=identifier, cmb=combo):
                path = cmb.itemData(idx)
                if path:
                    self._sound_manager.change_sound_mapping(ident, Path(path), skip_saving=True)
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
                self._has_changes = True

            upload_btn.clicked.connect(on_upload)
            grid.addWidget(upload_btn, row, 2)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            cur_vol = int(float(self._sound_manager.volume_mapping.get(identifier, sound_obj.standard_volume)) * 100)
            slider.setValue(cur_vol)
            grid.addWidget(slider, row, 3)

            vol_label = QLabel(f"{cur_vol}%")
            grid.addWidget(vol_label, row, 4)

            def on_slider_changed(val, ident=identifier, lbl=vol_label):
                lbl.setText(f"{val}%")
                self._sound_manager.change_volume_mapping(ident, float(val) / 100.0, skip_saving=True)

            slider.valueChanged.connect(on_slider_changed)

            play_btn = PlayButton(sound_obj, self._sound_box)
            play_btn.clicked.connect(lambda: setattr(self, "_has_changes", True))
            
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
        
    def has_changes(self) -> bool:
        return self._has_changes

    def save_changes(self):
        """Saves current sound settings to the SoundManager."""
        self._sound_manager._save_mappings()
        self._has_changes = False

class PlayButton(QPushButton):
    def __init__(self, sound:Sound, sound_box:SoundBox, parent=None) -> None:
        super().__init__("▶", parent)
        self._sound = sound
        self._sound_box = sound_box
        self.clicked.connect(self._on_click)
    
    def _on_click(self):
        self._sound_box.add_sound(self._sound, disable_periodic=True)