"""
Unit tests for wtFetcher module - testing telemetry data parsing
"""
import pytest
import sys
from pathlib import Path

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

from backend.wtFetcher import (
    TelemetryData, 
    WTUpdater, 
    TelemetryNotFoundException,
    TELEMETRY_INFORMATION,
    OPTIONAL_TELEMETRY
)


class TestTelemetryData:
    """Test the TelemetryData dataclass"""
    
    def test_telemetry_data_creation_minimal(self):
        """Test creating TelemetryData with minimal required fields"""
        data = TelemetryData(
            planetype="f-80a",
            flaps=0,
            gear=0,
            ias=200
        )
        assert data.planetype == "f-80a"
        assert data.flaps == 0
        assert data.gear == 0
        assert data.ias == 200
    
    def test_telemetry_data_creation_full(self):
        """Test creating TelemetryData with all fields"""
        data = TelemetryData(
            planetype="f-80a",
            flaps=50,
            gear=100,
            ias=300,
            lat=52.5200,
            lon=13.4050,
            airbrake=25,
            mach_speed=0.8
        )
        assert data.planetype == "f-80a"
        assert data.flaps == 50
        assert data.gear == 100
        assert data.ias == 300
        assert data.lat == 52.5200
        assert data.lon == 13.4050
        assert data.airbrake == 25
        assert data.mach_speed == 0.8
    
    def test_telemetry_data_defaults(self):
        """Test TelemetryData default values"""
        data = TelemetryData(
            planetype="f-80a",
            flaps=0,
            gear=0,
            ias=200
        )
        assert data.lat == 0
        assert data.lon == 0
        assert data.airbrake == 0
        assert data.mach_speed == 999.9


class TestWTUpdaterParsing:
    """Test the WTUpdater telemetry parsing functionality"""
    
    def test_parse_telemetry_basic(self):
        """Test parsing telemetry with all required fields"""
        updater = WTUpdater("localhost", debug_mode=True)
        
        source = {
            "airframe": "f-80a",
            "flaps, %": 50,
            "gearState": 1,
            "IAS, km/h": 300
        }
        
        result = updater._WTUpdater__parse_telemetry(source)
        assert isinstance(result, TelemetryData)
        assert result.planetype == "f-80a"
        assert result.flaps == 50
        assert result.gear == 1
        assert result.ias == 300
    
    def test_parse_telemetry_with_optional(self):
        """Test parsing telemetry with optional fields"""
        updater = WTUpdater("localhost", debug_mode=True)
        
        source = {
            "airframe": "f-80a",
            "flaps, %": 50,
            "gearState": 1,
            "IAS, km/h": 300,
            "lat": 52.5200,
            "lon": 13.4050,
            "airbrake, %": 25,
            "M": 0.8
        }
        
        result = updater._WTUpdater__parse_telemetry(source)
        assert result.lat == 52.5200
        assert result.lon == 13.4050
        assert result.airbrake == 25
        assert result.mach_speed == 0.8
    
    def test_parse_telemetry_fallback_to_optional_source(self):
        """Test parsing telemetry falls back to optional_source when key not in source"""
        updater = WTUpdater("localhost", debug_mode=True)
        
        source = {
            "airframe": "f-80a",
            "flaps, %": 50,
            "gearState": 1
        }
        
        optional_source = {
            "IAS, km/h": 300
        }
        
        result = updater._WTUpdater__parse_telemetry(source, optional_source)
        assert result.ias == 300
    
    def test_parse_telemetry_missing_required_field(self):
        """Test parsing telemetry raises exception when required field is missing"""
        updater = WTUpdater("localhost", debug_mode=True)
        
        source = {
            "airframe": "f-80a",
            "flaps, %": 50
            # Missing gearState and IAS
        }
        
        with pytest.raises(TelemetryNotFoundException):
            updater._WTUpdater__parse_telemetry(source)
    
    def test_parse_telemetry_alternative_keys(self):
        """Test parsing telemetry with alternative key names"""
        updater = WTUpdater("localhost", debug_mode=True)
        
        # Using alternative key "flapState" instead of "flaps, %"
        source = {
            "airframe": "f-80a",
            "flapState": 25,
            "gear, %": 50,
            "IAS, km/h": 300
        }
        
        result = updater._WTUpdater__parse_telemetry(source)
        assert result.flaps == 25
        assert result.gear == 50


class TestTelemetryConfiguration:
    """Test telemetry configuration constants"""
    
    def test_telemetry_information_structure(self):
        """Test that TELEMETRY_INFORMATION has expected structure"""
        assert isinstance(TELEMETRY_INFORMATION, dict)
        assert "planetype" in TELEMETRY_INFORMATION
        assert "flaps" in TELEMETRY_INFORMATION
        assert "gear" in TELEMETRY_INFORMATION
        assert "ias" in TELEMETRY_INFORMATION
    
    def test_telemetry_information_values_are_lists(self):
        """Test that all values in TELEMETRY_INFORMATION are lists"""
        for key, value in TELEMETRY_INFORMATION.items():
            assert isinstance(value, list)
            assert len(value) > 0
    
    def test_optional_telemetry_is_list(self):
        """Test that OPTIONAL_TELEMETRY is a list"""
        assert isinstance(OPTIONAL_TELEMETRY, list)
    
    def test_optional_telemetry_items_in_telemetry_info(self):
        """Test that all optional telemetry items are in TELEMETRY_INFORMATION"""
        for item in OPTIONAL_TELEMETRY:
            assert item in TELEMETRY_INFORMATION
