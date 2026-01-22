"""
Unit tests for Models module
"""
import pytest
import sys
from pathlib import Path

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

from Models.basic import Theme, THEME_NAMES


class TestTheme:
    """Test the Theme enumeration"""
    
    def test_theme_values(self):
        """Test that theme enum has expected values"""
        assert Theme.AUTO.value == 0
        assert Theme.LIGHT.value == 1
        assert Theme.DARK.value == 2
    
    def test_theme_names_exist(self):
        """Test that all themes have names"""
        assert Theme.LIGHT in THEME_NAMES
        assert Theme.DARK in THEME_NAMES
        assert Theme.AUTO in THEME_NAMES
    
    def test_theme_names_are_strings(self):
        """Test that theme names are strings"""
        for theme in [Theme.LIGHT, Theme.DARK, Theme.AUTO]:
            assert isinstance(THEME_NAMES[theme], str)
    
    def test_theme_count(self):
        """Test that we have exactly 3 themes"""
        assert len(Theme) == 3
        assert len(THEME_NAMES) == 3
