from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal
from Packages.Models.Plane import WTPlane, flapState
from backend.SoundEngine import Sound
from backend.SoundEngine.sounds import SpeedWarningSound, FlapSpeedWarningSound, GearSpeedWarningSound, FlapInfoSound
from backend.wtFetcher import TelemetryData
from backend.settings import WarningSettings
@dataclass
class thresholdSpeeds:
    gear:int
    frame:int
    frame_mach:None|float
    combat_flap:None|int
    start_flap:None|int
    landing_flap:None|int

@dataclass
class thresholdSettings:
    speed_warning_treshold:float
    min_diff:int
    max_diff:int

    mach_speed_threshold:float = 0.95
    mach_min_diff:float = 0.05
    mach_max_diff:float = 0.2
    
STANDADRD_SPEED_TRESHOLDS = thresholdSettings(0.9, 10, 50)

class PlaneSpeedWarningEngine(QObject):
    thresholds:thresholdSpeeds|None
    _speed_borders:thresholdSettings
    _plane_max_speeds:dict|None
    _current_warnings:list[Sound] = []
    _plane_flap_states:list[tuple[int,flapState]]|None
    _informed_flap_state: flapState = flapState.NONE
    # SIGNALS
    play_sound_signal = Signal(list)
    stop_sound_signal = Signal(list)
    
    def __init__(self,
                speed_warning_treshold:float|None = None, 
                min_diff:int|None = None, 
                max_diff:int|None = None, 
                mach_speed_threshold:float|None = None,
                mach_min_diff:float|None = None,
                mach_max_diff:float|None = None
                ):    
        super().__init__()
        self._plane_max_speeds = None
        self.thresholds = None
        self._speed_borders = STANDADRD_SPEED_TRESHOLDS
        
        if speed_warning_treshold is not None:
            self._speed_borders.speed_warning_treshold = speed_warning_treshold / 100
        if min_diff is not None:
            self._speed_borders.min_diff = min_diff
        if max_diff is not None:
            self._speed_borders.max_diff = max_diff
        if mach_speed_threshold is not None:
            self._speed_borders.mach_speed_threshold = mach_speed_threshold / 100
        if mach_min_diff is not None:
            self._speed_borders.mach_min_diff = mach_min_diff
        if mach_max_diff is not None:
            self._speed_borders.mach_max_diff = mach_max_diff
    
    
    def on_new_plane(self, plane:WTPlane):
        """Update plane data

        :param plane: the New Plane object
        :type plane: WTPlane
        """
        max_speeds = plane.get_max_speeds()
        if max_speeds is None:
            self.thresholds = None
            self._plane_max_speeds = None
            return
        else:
            self._plane_max_speeds = max_speeds
            self._calc_and_set_tresholds()
        
        self._plane_flap_states = plane.get_flap_deployment_thresholds()
        
    
    def on_new_telemetry(self, telemetry:TelemetryData):
        """Update telemetry data and recalculate warnings

        :param telemetry: the New Telemetry data
        :type telemetry: TelemetryData
        """
        warning_list:list[Sound] = []
        if telemetry is None or self.thresholds is None:
            return
        print(f"IAS: {telemetry.ias} | FLAPS: {telemetry.flaps} | GEAR: {telemetry.gear} | MACH: {telemetry.mach_speed} | TRESHOLDS: {self.thresholds}")
        
        if telemetry.ias is not None and self.thresholds is not None:
            if (telemetry.ias > self.thresholds.frame): #or (self.thresholds.frame_mach is not None and telemetry.mach_speed is not None and telemetry.mach_speed > self.thresholds.frame_mach):
                warning_list.append(SpeedWarningSound())
            if self.thresholds.frame_mach is not None and telemetry.mach_speed is not None and telemetry.mach_speed > self.thresholds.frame_mach:
                warning_list.append(SpeedWarningSound())
            
            if telemetry.ias > self.thresholds.gear and telemetry.gear > 0:
                warning_list.append(GearSpeedWarningSound())
            
            current_flap_tresh = self._get_current_flap_treshold(telemetry.flaps)
            if current_flap_tresh is not None and telemetry.ias > current_flap_tresh:
                warning_list.append(FlapSpeedWarningSound())
            
            if self._new_flap_avaliable(telemetry.ias, telemetry.flaps):
                warning_list.append(FlapInfoSound())
        
            new_warnings = self._add_new_warning_sounds(warning_list)
            old_warnings = self._pop_old_warning_sounds(warning_list)
            if len(old_warnings) > 0:
                self.stop_sound_signal.emit(old_warnings)
            if len(new_warnings) > 0:                
                self.play_sound_signal.emit(new_warnings)

    def on_new_threshold_settings(self, settings:WarningSettings):
        """Update Threshold settings

        :param settings: New Settings for the speed treshold calculation
        :type settings: WarningSettings
        """
        tresh_settings = thresholdSettings(
            speed_warning_treshold=settings.speed_treshold / 100.0,
            min_diff=settings.min_diff,
            max_diff=settings.max_diff
        )
        
        
        self._speed_borders = tresh_settings
        self._calc_and_set_tresholds()
            
    def _calc_and_set_tresholds(self) -> thresholdSpeeds|None:
        """
        Calculate the speed tresholds for the given max speeds and store them in self.thresholds
        
        :return: Beschreibung
        :rtype: thresholdSpeeds
        """
        max_speeds = self._plane_max_speeds
        if max_speeds is None:
            self.thresholds = None
            return None
        
        
        gear_tresh = get_treshold_value(max_speeds["gear"], self._speed_borders)
        frame_tresh = get_treshold_value(max_speeds["frame"], self._speed_borders)
        frame_mach_tresh = get_treshold_value(max_speeds.get("frame mach",None), self._speed_borders, speed_in_mach=True)
        combat_tresh = get_treshold_value(max_speeds.get("combat",None), self._speed_borders)
        start_tresh = get_treshold_value(max_speeds.get("start",None), self._speed_borders)
        landing_tresh = get_treshold_value(max_speeds.get("landing",None), self._speed_borders)
        
        assert isinstance(gear_tresh, int)
        assert isinstance(frame_tresh, int)
        assert isinstance(frame_mach_tresh, float) or frame_mach_tresh is None
        self.thresholds = thresholdSpeeds(
            gear=gear_tresh,
            frame=frame_tresh,
            frame_mach=frame_mach_tresh,
            combat_flap=int(combat_tresh) if combat_tresh is not None else None,
            start_flap=int(start_tresh) if start_tresh is not None else None,
            landing_flap=int(landing_tresh) if landing_tresh is not None else None
        )
        return self.thresholds
    
    def _get_current_flap_state(self, current_flap_percentage:int) -> flapState:
        """Get the current flap state based on the current flap deployment percentage

        :param current_flap_percentage: Current flap deployment in percentage
        :type current_flap_percentage: int
        :return: Current flap state
        :rtype: flapState
        """
        if self._plane_flap_states is None:
            return flapState.NONE
        applicable_states = [state for state in self._plane_flap_states if current_flap_percentage <= state[0]]
        # applicable_states = [(tresh, flap_state) for tresh, flap_state in self._plane_flap_states if current_flap_percentage >= tresh]
        if not applicable_states:
            return flapState.NONE
        # get the state with the highest percentage that is still less than or equal to the current percentage
        applicable_state = min(applicable_states, key=lambda x: x[0])
        
        return applicable_state[1]
    
    def _get_current_flap_treshold(self, current_flap_percentage:int) -> int|None:
        """Get the current flap speed treshold based on the current flap deployment percentage

        :param current_flap_percentage: Current flap deployment in percentage
        :type current_flap_percentage: int
        :return: Current flap speed treshold
        :rtype: int|None
        """
        if self.thresholds is None:
            return None
        current_state = self._get_current_flap_state(current_flap_percentage)
        
        match current_state:
            case flapState.COMBAT:
                return self.thresholds.combat_flap
            case flapState.START:
                return self.thresholds.start_flap
            case flapState.LANDING:
                return self.thresholds.landing_flap
            case _:
                return None
    
    def _new_flap_avaliable(self, current_speed:int, current_flap_percentage:int) -> bool:
        
        FLAP_STATES = [
            flapState.NONE,
            flapState.COMBAT,
            flapState.START,
            flapState.LANDING
        ]
        
        if self._plane_flap_states is None or self._plane_max_speeds is None:
            return False
        
        safe_state = flapState.NONE
        for tresh ,flap_state in self._plane_flap_states[::-1]:
            if flap_state == flapState.NONE:
                safe_state = flapState.NONE
                break
            if current_speed < self._plane_max_speeds.get(flap_state.value, 0):
                safe_state = flap_state
                break
            
            
            
        informed_level = FLAP_STATES.index(self._informed_flap_state) if self._informed_flap_state is not None else 0
        current_level = FLAP_STATES.index(self._get_current_flap_state(current_flap_percentage))
        safe_level = FLAP_STATES.index(safe_state)
        
        if safe_level > informed_level:
            self._informed_flap_state = safe_state
            if safe_level > current_level:
                return True
        elif safe_level < informed_level:
            self._informed_flap_state = safe_state
        return False
        
    def _add_new_warning_sounds(self, new_warnings:list[Sound]) -> list[Sound]:
        """Compare new warnings with current warnings and return only the new ones

        :param new_warnings: List of newly generated warnings
        :type new_warnings: list[Sound]
        :return: List of new warnings that were not present in current warnings
        :rtype: list[Sound]
        """
        current_ids = [sound.identifier for sound in self._current_warnings]
        new_sounds = [sound for sound in new_warnings if sound.identifier not in current_ids]
        self._current_warnings.extend(new_sounds)
        
        return new_sounds
    
    def _pop_old_warning_sounds(self, new_warnings:list[Sound]) -> list[Sound]:
        """Compare new warnings with current warnings and return only those that are no longer present

        :param new_warnings: List of newly generated warnings
        :type new_warnings: list[Sound]
        :return: List of old warnings that are no longer present in new warnings
        :rtype: list[Sound]
        """
        new_ids = [sound.identifier for sound in new_warnings]
        old_sounds = [sound for sound in self._current_warnings if sound.identifier not in new_ids]
        
        for sound in old_sounds:
            self._current_warnings.remove(sound)
        
        return old_sounds
    
def get_treshold_value(max_speed:int|None, tresholds:thresholdSettings, speed_in_mach:bool = False) -> float|int|None:
    """ Calculates the Treshold for the given Speed and the settings defined in tresholds."""
    if max_speed is None:
        return None
    if speed_in_mach:
        if max_speed == 999.9:
            return None
        calc_tresh = max_speed * tresholds.mach_speed_threshold
        max_tresh = max_speed - tresholds.mach_min_diff
        min_tresh = max_speed - tresholds.mach_max_diff
    else:
        calc_tresh = max_speed * tresholds.speed_warning_treshold
        max_tresh = max_speed - tresholds.min_diff
        min_tresh = max_speed - tresholds.max_diff
    result = None
    
    if calc_tresh > max_tresh:
        result = max_tresh
    elif calc_tresh < min_tresh:
        result = min_tresh
    else:
        result = calc_tresh
    
    if not speed_in_mach:
        result = int(result)
    return result