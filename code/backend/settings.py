from dataclasses import dataclass, field
from typing import Any

from Models import Theme, THEME_NAMES
from Packages.settings_collection import SettingsCollection
from Packages.local_db import LocalDB

DB = LocalDB()

@dataclass
class SoundProperties:
    """Properties for a Sound Notification"""
    name: str
    file_path: str
    volume: float = 1.0
    overlapping: bool = False
    

@dataclass    
class GeneralSettings:
    """Settings For the Whole Programm
    """
    ip: str = "127.0.0.1"
    intervall: int = 100
    theme: Theme = Theme.AUTO
    
    def to_dict(self):
        return {
            "ip": self.ip,
            "intervall": self.intervall,
            "theme": self.theme.value,
        }

@dataclass
class WarningSettings:
    """Settings for when Warnings and Informations are triggered"""
    speed_treshold: float = 90.0
    min_diff: int = 10
    max_diff: int = 50

    mach_threshold: float = 95.0
    min_mach_diff: float = 0.05
    max_mach_diff: float = 0.2
    
@dataclass
class SoundSettings:
    """Settings for Sound Notifications"""
    master_volume: float = 1.0
    sounds: dict[str, SoundProperties] = field(default_factory=dict)
    
    @classmethod
    def load_from_db(cls):
        data = DB.get_global_settings().get("sounds", {})
        return cls.from_dict(data)
    
    def to_dict(self):
        return {
            "master_volume": self.master_volume,
            "sounds": {k: v.__dict__ for k, v in self.sounds.items()}
        }
        
    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        master_volume = data.get("master_volume", 1.0)
        sounds_data = data.get("sounds", {})
        sounds = {k: SoundProperties(**v) for k, v in sounds_data.items()}
        return cls(master_volume=master_volume, sounds=sounds)
        
class GlobalSettings(object):
    """Global Settings Object containing all Settings Groups
    """
    general: GeneralSettings
    warning: WarningSettings
    sounds: SoundSettings

    def __init__(self, general:GeneralSettings|None=None, warning:WarningSettings|None=None, sound:SoundSettings|None=None):
        self.general = general if general is not None else GeneralSettings()
        self.warning = warning if warning is not None else WarningSettings()
        self.sounds = sound if sound is not None else SoundSettings()
        
    def to_dict(self) -> dict:
        return {
            "general": self.general.to_dict(),
            "warning": self.warning.__dict__,
            "sounds": self.sounds.__dict__,
        }
        
    def __eq__(self, value: object) -> bool:
        assert isinstance(value, GlobalSettings)
        return self.to_dict() == value.to_dict()
    
    @classmethod
    def from_dict(cls, data:dict):
        settings = cls()
        if isinstance(dict(data.get("general", {})).get("theme", None), int):
            data["general"]["theme"] = Theme(data["general"]["theme"])
        
        settings.general = GeneralSettings(**data.get("general", {}))
        settings.warning = WarningSettings(**data.get("warning", {}))
        settings.sounds = SoundSettings(**data.get("sounds", {}))
        return settings
    
    @classmethod
    def from_settingsCollection(cls,collection:SettingsCollection):
        themes_reverse = {v: k for k, v in THEME_NAMES.items()}
        
        general = GeneralSettings(
            ip=collection.ip,
            intervall=collection.intervall,
            theme=themes_reverse.get(collection.theme, Theme.AUTO)
        )
        warning = WarningSettings(
            speed_treshold=collection.speed_warning_treshold,
            min_diff=collection.speed_warning_min_diff,
            max_diff=collection.speed_warning_max_diff
        )
        return cls(general=general, warning=warning)