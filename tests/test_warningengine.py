"""
Unit tests for backend/warningEngine.py - testing warning engine threshold calculations
"""
import pytest
import sys
from pathlib import Path

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

from backend.warningEngine import (
    thresholdSpeeds,
    thresholdSettings,
    STANDADRD_SPEED_TRESHOLDS
)


class TestThresholdSpeeds:
    """Test the thresholdSpeeds dataclass"""
    
    def test_threshold_speeds_creation(self):
        """Test creating thresholdSpeeds with all fields"""
        thresholds = thresholdSpeeds(
            gear=250,
            frame=600,
            frame_mach=0.9,
            combat_flap=400,
            start_flap=300,
            landing_flap=200
        )
        assert thresholds.gear == 250
        assert thresholds.frame == 600
        assert thresholds.frame_mach == 0.9
        assert thresholds.combat_flap == 400
        assert thresholds.start_flap == 300
        assert thresholds.landing_flap == 200
    
    def test_threshold_speeds_with_none(self):
        """Test creating thresholdSpeeds with None values"""
        thresholds = thresholdSpeeds(
            gear=250,
            frame=600,
            frame_mach=None,
            combat_flap=None,
            start_flap=None,
            landing_flap=None
        )
        assert thresholds.gear == 250
        assert thresholds.frame == 600
        assert thresholds.frame_mach is None
        assert thresholds.combat_flap is None
        assert thresholds.start_flap is None
        assert thresholds.landing_flap is None


class TestThresholdSettings:
    """Test the thresholdSettings dataclass"""
    
    def test_threshold_settings_basic(self):
        """Test creating thresholdSettings with basic fields"""
        settings = thresholdSettings(
            speed_warning_treshold=0.85,
            min_diff=15,
            max_diff=45
        )
        assert settings.speed_warning_treshold == 0.85
        assert settings.min_diff == 15
        assert settings.max_diff == 45
    
    def test_threshold_settings_with_mach(self):
        """Test creating thresholdSettings with mach fields"""
        settings = thresholdSettings(
            speed_warning_treshold=0.9,
            min_diff=10,
            max_diff=50,
            mach_speed_threshold=0.92,
            mach_min_diff=0.04,
            mach_max_diff=0.18
        )
        assert settings.mach_speed_threshold == 0.92
        assert settings.mach_min_diff == 0.04
        assert settings.mach_max_diff == 0.18
    
    def test_threshold_settings_defaults(self):
        """Test thresholdSettings default mach values"""
        settings = thresholdSettings(
            speed_warning_treshold=0.9,
            min_diff=10,
            max_diff=50
        )
        # Check default mach values
        assert settings.mach_speed_threshold == 0.95
        assert settings.mach_min_diff == 0.05
        assert settings.mach_max_diff == 0.2


class TestStandardThresholds:
    """Test the STANDADRD_SPEED_TRESHOLDS constant"""
    
    def test_standard_thresholds_values(self):
        """Test that standard thresholds have expected values"""
        assert STANDADRD_SPEED_TRESHOLDS.speed_warning_treshold == 0.9
        assert STANDADRD_SPEED_TRESHOLDS.min_diff == 10
        assert STANDADRD_SPEED_TRESHOLDS.max_diff == 50
        assert STANDADRD_SPEED_TRESHOLDS.mach_speed_threshold == 0.95
        assert STANDADRD_SPEED_TRESHOLDS.mach_min_diff == 0.05
        assert STANDADRD_SPEED_TRESHOLDS.mach_max_diff == 0.2
    
    def test_standard_thresholds_is_threshold_settings(self):
        """Test that standard thresholds is a thresholdSettings instance"""
        assert isinstance(STANDADRD_SPEED_TRESHOLDS, thresholdSettings)
