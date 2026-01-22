"""
Unit tests for mapinfo module - testing coordinate calculations and utility functions
"""
import pytest
import sys
from pathlib import Path

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

from Packages.WarThunder.mapinfo import hypotenuse, coord_bearing, coord_dist


class TestHypotenuse:
    """Test the hypotenuse calculation function"""
    
    def test_hypotenuse_basic(self):
        """Test basic 3-4-5 triangle"""
        assert hypotenuse(3, 4) == 5.0
    
    def test_hypotenuse_zero(self):
        """Test with one side being zero"""
        assert hypotenuse(0, 5) == 5.0
        assert hypotenuse(5, 0) == 5.0
    
    def test_hypotenuse_both_zero(self):
        """Test with both sides being zero"""
        assert hypotenuse(0, 0) == 0.0
    
    def test_hypotenuse_decimal(self):
        """Test with decimal values"""
        result = hypotenuse(1.5, 2.0)
        assert abs(result - 2.5) < 0.0001


class TestCoordBearing:
    """Test the coordinate bearing calculation function"""
    
    def test_bearing_north(self):
        """Test bearing directly north"""
        # From equator to north
        bearing = coord_bearing(0, 0, 1, 0)
        assert abs(bearing - 0) < 1  # Should be close to 0 degrees (north)
    
    def test_bearing_east(self):
        """Test bearing directly east"""
        bearing = coord_bearing(0, 0, 0, 1)
        assert abs(bearing - 90) < 1  # Should be close to 90 degrees (east)
    
    def test_bearing_south(self):
        """Test bearing directly south"""
        bearing = coord_bearing(1, 0, 0, 0)
        assert abs(bearing - 180) < 1  # Should be close to 180 degrees (south)
    
    def test_bearing_west(self):
        """Test bearing directly west"""
        bearing = coord_bearing(0, 1, 0, 0)
        assert abs(bearing - 270) < 1  # Should be close to 270 degrees (west)
    
    def test_bearing_same_point(self):
        """Test bearing when points are the same"""
        bearing = coord_bearing(45.0, 10.0, 45.0, 10.0)
        assert 0 <= bearing <= 360  # Should return a valid angle


class TestCoordDist:
    """Test the coordinate distance calculation function"""
    
    def test_distance_same_point(self):
        """Test distance between same point"""
        dist = coord_dist(0, 0, 0, 0)
        assert abs(dist) < 0.001  # Should be approximately 0
    
    def test_distance_equator(self):
        """Test distance along equator"""
        # 1 degree longitude at equator is approximately 111 km
        dist = coord_dist(0, 0, 0, 1)
        assert 110 < dist < 112
    
    def test_distance_meridian(self):
        """Test distance along meridian"""
        # 1 degree latitude is approximately 111 km
        dist = coord_dist(0, 0, 1, 0)
        assert 110 < dist < 112
    
    def test_distance_symmetry(self):
        """Test that distance is symmetric"""
        dist1 = coord_dist(10, 20, 30, 40)
        dist2 = coord_dist(30, 40, 10, 20)
        assert abs(dist1 - dist2) < 0.001
    
    def test_distance_realistic_scenario(self):
        """Test realistic game scenario distance"""
        # Example: distance between two points that might be in a game
        dist = coord_dist(52.5200, 13.4050, 48.8566, 2.3522)  # Berlin to Paris
        assert 850 < dist < 900  # Approximately 877 km
