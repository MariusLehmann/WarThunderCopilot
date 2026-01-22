"""
Unit tests for backend/settings.py - testing settings data structures and conversions
"""
import pytest
import sys
from pathlib import Path

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

from backend.settings import (
    GeneralSettings,
    WarningSettings,
    SoundSettings,
    GlobalSettings
)
from Models.basic import Theme


class TestGeneralSettings:
    """Test the GeneralSettings dataclass"""
    
    def test_general_settings_defaults(self):
        """Test GeneralSettings default values"""
        settings = GeneralSettings()
        assert settings.ip == "0.0.0.0"
        assert settings.intervall == 500
        assert settings.theme == Theme.AUTO
    
    def test_general_settings_custom(self):
        """Test GeneralSettings with custom values"""
        settings = GeneralSettings(
            ip="192.168.1.100",
            intervall=1000,
            theme=Theme.DARK
        )
        assert settings.ip == "192.168.1.100"
        assert settings.intervall == 1000
        assert settings.theme == Theme.DARK
    
    def test_general_settings_to_dict(self):
        """Test GeneralSettings conversion to dict"""
        settings = GeneralSettings(
            ip="127.0.0.1",
            intervall=250,
            theme=Theme.LIGHT
        )
        result = settings.to_dict()
        assert result["ip"] == "127.0.0.1"
        assert result["intervall"] == 250
        assert result["theme"] == Theme.LIGHT.value


class TestWarningSettings:
    """Test the WarningSettings dataclass"""
    
    def test_warning_settings_defaults(self):
        """Test WarningSettings default values"""
        settings = WarningSettings()
        assert settings.speed_treshold == 90.0
        assert settings.min_diff == 10
        assert settings.max_diff == 50
        assert settings.mach_threshold == 95.0
        assert settings.min_mach_diff == 0.05
        assert settings.max_mach_diff == 0.2
    
    def test_warning_settings_custom(self):
        """Test WarningSettings with custom values"""
        settings = WarningSettings(
            speed_treshold=85.0,
            min_diff=15,
            max_diff=60,
            mach_threshold=92.0,
            min_mach_diff=0.03,
            max_mach_diff=0.15
        )
        assert settings.speed_treshold == 85.0
        assert settings.min_diff == 15
        assert settings.max_diff == 60
        assert settings.mach_threshold == 92.0
        assert settings.min_mach_diff == 0.03
        assert settings.max_mach_diff == 0.15


class TestGlobalSettings:
    """Test the GlobalSettings class"""
    
    def test_global_settings_defaults(self):
        """Test GlobalSettings with default values"""
        settings = GlobalSettings()
        assert isinstance(settings.general, GeneralSettings)
        assert isinstance(settings.warning, WarningSettings)
        assert settings.general.ip == "0.0.0.0"
        assert settings.warning.speed_treshold == 90.0
    
    def test_global_settings_custom(self):
        """Test GlobalSettings with custom components"""
        general = GeneralSettings(ip="10.0.0.1", intervall=300)
        warning = WarningSettings(speed_treshold=88.0)
        
        settings = GlobalSettings(general=general, warning=warning)
        assert settings.general.ip == "10.0.0.1"
        assert settings.general.intervall == 300
        assert settings.warning.speed_treshold == 88.0
    
    def test_global_settings_to_dict(self):
        """Test GlobalSettings conversion to dict"""
        settings = GlobalSettings()
        result = settings.to_dict()
        
        assert "general" in result
        assert "warning" in result
        assert result["general"]["ip"] == "0.0.0.0"
        assert result["warning"]["speed_treshold"] == 90.0
    
    def test_global_settings_from_dict(self):
        """Test GlobalSettings creation from dict"""
        data = {
            "general": {
                "ip": "192.168.0.50",
                "intervall": 750,
                "theme": 2  # Dark theme
            },
            "warning": {
                "speed_treshold": 87.5,
                "min_diff": 12,
                "max_diff": 55
            }
        }
        
        settings = GlobalSettings.from_dict(data)
        assert settings.general.ip == "192.168.0.50"
        assert settings.general.intervall == 750
        assert settings.general.theme == Theme.DARK
        assert settings.warning.speed_treshold == 87.5
        assert settings.warning.min_diff == 12
    
    def test_global_settings_equality(self):
        """Test GlobalSettings equality comparison"""
        settings1 = GlobalSettings()
        settings2 = GlobalSettings()
        
        assert settings1 == settings2
        
        # Modify one and check inequality
        settings2.general.ip = "192.168.1.1"
        assert settings1 != settings2
    
    def test_global_settings_from_dict_partial(self):
        """Test GlobalSettings from dict with partial data"""
        data = {
            "general": {
                "ip": "172.16.0.1"
            }
        }
        
        settings = GlobalSettings.from_dict(data)
        # Should use provided IP but defaults for other values
        assert settings.general.ip == "172.16.0.1"
        assert settings.general.intervall == 500  # default
        assert settings.warning.speed_treshold == 90.0  # default
