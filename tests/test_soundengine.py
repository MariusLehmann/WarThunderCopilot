"""
Unit tests for backend SoundEngine - testing sound management and queue functionality
"""
import pytest
import sys
from pathlib import Path
import time

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

from backend.SoundEngine.general import Sound, PlayableSound, SoundManager
from backend.SoundEngine.sounds import (
    SpeedWarningSound,
    FlapSpeedWarningSound,
    GearSpeedWarningSound,
    FlapInfoSound
)


class TestSound:
    """Test the Sound base class"""
    
    def test_sound_creation_minimal(self):
        """Test creating Sound with minimal parameters"""
        sound = Sound(
            name="test_sound",
            standard_path="/path/to/sound.wav"
        )
        assert sound.name == "test_sound"
        assert sound.standard_path == "/path/to/sound.wav"
        assert sound.identifier == "test_sound"
        assert sound.intervall is None
        assert sound.priority_playback is False
    
    def test_sound_creation_full(self):
        """Test creating Sound with all parameters"""
        sound = Sound(
            name="warning",
            standard_path="/path/to/warning.wav",
            intervall=2,
            identifier="custom_id",
            description="Test warning sound",
            priority_playback=True,
            volume=0.8
        )
        assert sound.name == "warning"
        assert sound.standard_path == "/path/to/warning.wav"
        assert sound.intervall == 2
        assert sound.identifier == "custom_id"
        assert sound.description == "Test warning sound"
        assert sound.priority_playback is True
        assert sound.standard_volume == 0.8
    
    def test_sound_identifier_defaults_to_name(self):
        """Test that identifier defaults to name if not provided"""
        sound = Sound(
            name="my_sound",
            standard_path="/path/to/sound.wav"
        )
        assert sound.identifier == "my_sound"


class TestPlayableSound:
    """Test the PlayableSound class"""
    
    def test_playable_sound_creation(self):
        """Test creating PlayableSound"""
        playable = PlayableSound(
            path="/path/to/sound.wav",
            intervall=1,
            volume=0.75,
            identifier="test_id"
        )
        assert playable.path == "/path/to/sound.wav"
        assert playable.intervall == 1
        assert playable.volume == 0.75
        assert playable.identifier == "test_id"
    
    def test_playable_sound_volume_validation(self):
        """Test that PlayableSound validates volume range"""
        # Valid volumes
        PlayableSound("/path/to/sound.wav", None, 0.0, "id1")
        PlayableSound("/path/to/sound.wav", None, 0.5, "id2")
        PlayableSound("/path/to/sound.wav", None, 1.0, "id3")
        
        # Invalid volumes should raise assertion error
        with pytest.raises(AssertionError):
            PlayableSound("/path/to/sound.wav", None, -0.1, "id4")
        
        with pytest.raises(AssertionError):
            PlayableSound("/path/to/sound.wav", None, 1.1, "id5")
    
    def test_playable_sound_without_intervall(self):
        """Test PlayableSound with no intervall (one-shot sound)"""
        playable = PlayableSound(
            path="/path/to/sound.wav",
            intervall=None,
            volume=0.5,
            identifier="oneshot"
        )
        assert playable.intervall is None


class TestPredefinedSounds:
    """Test the predefined sound classes"""
    
    def test_speed_warning_sound(self):
        """Test SpeedWarningSound configuration"""
        sound = SpeedWarningSound()
        assert sound.name == "speed_warning"
        assert sound.intervall == 1
        assert sound.identifier == "speed_warning"
        assert sound.description == "speed too high for the airframe"
        assert sound.priority_playback is False
    
    def test_flap_speed_warning_sound(self):
        """Test FlapSpeedWarningSound configuration"""
        sound = FlapSpeedWarningSound()
        assert sound.name == "flap_speed_warning"
        assert sound.intervall == 1
        assert sound.identifier == "flap_speed_warning"
        assert sound.description == "speed too high for current flap setting"
    
    def test_gear_speed_warning_sound(self):
        """Test GearSpeedWarningSound configuration"""
        sound = GearSpeedWarningSound()
        assert sound.name == "gear_speed_warning"
        assert sound.intervall == 1
        assert sound.identifier == "gear_speed_warning"
        assert sound.description == "speed too high for gear deployed"
    
    def test_flap_info_sound(self):
        """Test FlapInfoSound configuration"""
        sound = FlapInfoSound()
        assert sound.name == "flap_info"
        assert sound.intervall is None
        assert sound.identifier == "flap_available_info"
        assert sound.description == "info sound for flap deployment availability"
        assert sound.priority_playback is True
    
    def test_all_sounds_have_paths(self):
        """Test that all predefined sounds have valid paths"""
        sounds = [
            SpeedWarningSound(),
            FlapSpeedWarningSound(),
            GearSpeedWarningSound(),
            FlapInfoSound()
        ]
        for sound in sounds:
            assert sound.standard_path is not None
            assert len(str(sound.standard_path)) > 0


class TestSoundManagerBasics:
    """Test basic SoundManager functionality without database dependencies"""
    
    def test_sound_manager_master_volume_clamping(self):
        """Test that master volume is clamped to valid range"""
        manager = SoundManager()
        
        # Set volume below 0
        manager.change_master_volume(-0.5, skip_saving=True)
        assert manager.master_volume == 0.0
        
        # Set volume above 1
        manager.change_master_volume(1.5, skip_saving=True)
        assert manager.master_volume == 1.0
        
        # Set valid volume
        manager.change_master_volume(0.7, skip_saving=True)
        assert manager.master_volume == 0.7
    
    def test_sound_manager_get_playable_sound(self):
        """Test getting a PlayableSound from a Sound"""
        manager = SoundManager()
        
        sound = Sound(
            name="test",
            standard_path="/test/path.wav",
            intervall=2,
            identifier="test_id",
            volume=0.8
        )
        
        playable = manager.get_playable_sound(sound)
        
        assert isinstance(playable, PlayableSound)
        assert playable.identifier == "test_id"
        assert playable.intervall == 2
        # Volume should be affected by master volume
        assert playable.volume <= 0.8
