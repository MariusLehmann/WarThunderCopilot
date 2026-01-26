"""
Unit tests for code/settings.py - testing configuration constants
"""
import pytest
import sys
from pathlib import Path

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

import settings as app_settings


class TestDebugMode:
    """Test that DEBUG_MODE is properly configured"""
    
    def test_debug_mode_is_false(self):
        """Test that DEBUG_MODE is set to False for production"""
        assert app_settings.DEBUG_MODE is False, \
            "DEBUG_MODE must be False in production code. Set DEBUG_MODE = False in code/settings.py"
    
    def test_debug_mode_is_boolean(self):
        """Test that DEBUG_MODE is a boolean value"""
        assert isinstance(app_settings.DEBUG_MODE, bool), \
            "DEBUG_MODE must be a boolean value (True or False)"
    
    def test_log_level_reflects_debug_mode(self):
        """Test that LOG_LEVEL is set correctly based on DEBUG_MODE"""
        if app_settings.DEBUG_MODE:
            assert app_settings.LOG_LEVEL == 'DEBUG', \
                "LOG_LEVEL should be 'DEBUG' when DEBUG_MODE is True"
        else:
            assert app_settings.LOG_LEVEL == 'INFO', \
                "LOG_LEVEL should be 'INFO' when DEBUG_MODE is False"
