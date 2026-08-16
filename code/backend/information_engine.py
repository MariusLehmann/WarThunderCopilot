from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal, Slot

from .settings import WarningSettings, GlobalSettings

from Packages.local_db import LocalDB
from Models import Plane
from wt_dataclasses import FlapState, GENERAL_FLAP_STATES
from backend.SoundEngine import WT_Sound

SPEED_HISTORY_LENGTH = 50  # Number of recent speed differences to keep for threshold checks
ACCELERATION_WINDOW_SIZE = 5  # Number of recent speed differences used to compute the mean acceleration

@dataclass
class SpeedThreshold:
    warning_speed: int | float
    fatal_speed: int | float  
    
    def __init__(self, fatal_speed:int | float, warning_settings:WarningSettings, speed_in_mach:bool=False):
        self.fatal_speed = fatal_speed
        self.warning_speed = _get_threshold_value(fatal_speed, warning_settings, speed_in_mach)
        
@dataclass
class CurrentPlaneThresholds:
    """Class to hold the current warning thresholds for a plane."""
    gear: SpeedThreshold
    frame: SpeedThreshold
    frame_mach: SpeedThreshold | None 
    
    flaps: dict[str, SpeedThreshold] = field(default_factory=lambda: {state.value: SpeedThreshold(float('inf'), WarningSettings()) for state in GENERAL_FLAP_STATES})

class AcousticInformationEngine(QObject):
    # Signals
    S_NewInformationSounds = Signal(list)
    
    
    _plane: Plane | None
    _warning_settings: WarningSettings
    _current_thresholds: CurrentPlaneThresholds | None
    
    __last_informed_flap_state:FlapState
    __gear_deployable_informed:bool = False
        
    def __init__(self):
        super().__init__()
        db = LocalDB()
        
        self._warning_settings = GlobalSettings.from_dict(db.get_global_settings()).warning
        self.__last_informed_flap_state = FlapState.NONE
        self.__speed_diff_histories: dict[str, list[float | int]] = {}
        
    @Slot(Plane)
    def on_new_telemetry_or_plane(self, plane: Plane):
        """Update the current plane and its information engine.

        :param plane: The new Plane object.
        :type plane: Plane
        """
        self._plane = plane
        
        self.__calculate_plane_thresholds()
        assert self._current_thresholds is not None, "Current thresholds should not be None after calculation."
        informations = set()
        
        current_safe_flap_state = self.__get_safe_flap_state()
        current_flap_state = self.__get_current_flap_state()
        current_speed = self._plane.telemetry.ias
        
        
        # Flap Deployable Information
        if current_safe_flap_state != self.__last_informed_flap_state:
            if current_safe_flap_state > self.__last_informed_flap_state:
                informations.add(WT_Sound.FlapLevelAvaliable)
            
            self.__last_informed_flap_state = current_safe_flap_state
        
        # Gear Deployable Information
        if current_speed < self._current_thresholds.gear.fatal_speed and not self.__gear_deployable_informed:
            informations.add(WT_Sound.GearDeployable)
            self.__gear_deployable_informed = True
        elif current_speed >= self._current_thresholds.gear.fatal_speed and self.__gear_deployable_informed:
            self.__gear_deployable_informed = False
            
        # Speed Warnings
        if self.__threshold_exceeded_warning("frame", current_speed, self._current_thresholds.frame):
            informations.add(WT_Sound.FrameSpeedWarning)
        if self._current_thresholds.frame_mach is not None and self.__threshold_exceeded_warning("frame_mach", self._plane.telemetry.mach_speed, self._current_thresholds.frame_mach):
            informations.add(WT_Sound.FrameSpeedWarning)
        if self.__threshold_exceeded_warning("gear", current_speed, self._current_thresholds.gear) and self._plane.telemetry.gear > 0:
            informations.add(WT_Sound.GearSpeedWarning)
        
        current_flap_tresh = self._current_thresholds.flaps.get(current_flap_state.value, None)
        if current_flap_tresh is not None and self.__threshold_exceeded_warning(f"flap", current_speed, current_flap_tresh):
            informations.add(WT_Sound.FlapSpeedWarning)
        
        if informations:
            self.S_NewInformationSounds.emit(list(informations))
        
    @Slot()
    def on_no_plane(self):
        """Handle the case when there is no current plane."""
        self._plane = None
        self._current_thresholds = None
        
    @Slot(WarningSettings)
    def on_new_warning_settings(self, warning_settings: WarningSettings):
        """Update the warning settings and recalculate plane information if a plane is present.

        :param warning_settings: The new WarningSettings object.
        :type warning_settings: WarningSettings
        """
        self._warning_settings = warning_settings
        
        if self._plane is not None:
            self.__calculate_plane_thresholds()
    
    def __threshold_exceeded_warning(self, name:str, current_speed: float | int, threshold: SpeedThreshold) -> bool:
        """Decide whether a threshold-exceeded warning should be issued.

        Besides the raw speed/threshold comparison, the recent acceleration is taken
        into account: a warning is only issued while the plane is still actively
        speeding up towards the threshold. If the plane is not accelerating (constant
        speed or decelerating), no warning is issued even though the warning speed is
        currently exceeded - e.g. when a plane's maximum possible speed only lies
        slightly above the warning threshold.

        :param name: Identifier for the threshold being checked (used to keep a
            separate history per threshold).
        :type name: str
        :param current_speed: The plane's current speed.
        :type current_speed: float | int
        :param threshold: The threshold to check against.
        :type threshold: SpeedThreshold
        :return: True if a warning should be issued, False otherwise.
        :rtype: bool
        """
        if threshold is None:
            return False

        hist = self.__speed_diff_histories.setdefault(name, [])
        hist.append(current_speed - threshold.warning_speed)
        if len(hist) > SPEED_HISTORY_LENGTH:
            hist.pop(0)

        if current_speed < threshold.warning_speed:
            # Warning speed not (yet) reached - nothing to warn about.
            return False

        # if len(hist) < ACCELERATION_WINDOW_SIZE:
        #     # Not enough data yet to judge whether the plane is still accelerating.
        #     return False

        # Mean acceleration over a sliding window of the most recent history entries,
        # to smooth out noisy telemetry.
        accelerations = []
        for i in range(0, (len(hist)-ACCELERATION_WINDOW_SIZE)+1):
            window = hist[i:i+ACCELERATION_WINDOW_SIZE]
            acc = [window[j] - window[j - 1] for j in range(1, len(window))]
            cum_acc = sum(acc)
            mean_acc = cum_acc / len(acc) if len(acc) > 0 else 0
            accelerations.append(mean_acc)
            
        # window = hist[-(ACCELERATION_WINDOW_SIZE + 1):]
        # accelerations = [window[i] - window[i - 1] for i in range(1, len(window))]
        # mean_acceleration = sum(accelerations) / len(accelerations)
        # if sum(accelerations) / len(accelerations) < 0:
        #     # Not accelerating (anymore) - e.g. cruising just above the warning
        #     # threshold at the plane's max speed. No need to warn.
        #     return False

        # TODO: instead of only checking whether the plane is still accelerating,
        # predict whether the fatal speed will actually be reached within the next
        # x seconds based on the recorded history, and only warn in that case.
        return True


    def __calculate_plane_thresholds(self):
        """Calculate the warning thresholds for the current plane based on the warning settings."""
        if self._plane is None:
            raise ValueError("No current plane to calculate thresholds for.")
        
        basic_limits = self._plane.get_current_max_speeds()
        
        gear_thresh = SpeedThreshold(basic_limits.gear, self._warning_settings)
        frame_thresh = SpeedThreshold(basic_limits.frame, self._warning_settings)
        frame_mach_thresh = SpeedThreshold(basic_limits.frame_mach, self._warning_settings, speed_in_mach=True) if basic_limits.frame_mach is not None else SpeedThreshold(float('inf'), self._warning_settings, speed_in_mach=True)
        
        combat_flap_tresh = SpeedThreshold(basic_limits.combat_flap, self._warning_settings) if basic_limits.combat_flap is not None else SpeedThreshold(float('inf'), self._warning_settings)
        start_flap_tresh = SpeedThreshold(basic_limits.start_flap, self._warning_settings) if basic_limits.start_flap is not None else SpeedThreshold(float('inf'), self._warning_settings)
        landing_flap_tresh = SpeedThreshold(basic_limits.landing_flap, self._warning_settings) if basic_limits.landing_flap is not None else SpeedThreshold(float('inf'), self._warning_settings)

        flap_thresholds = {
            FlapState.COMBAT.value: combat_flap_tresh,
            FlapState.START.value: start_flap_tresh,
            FlapState.LANDING.value: landing_flap_tresh
        }
        
        self._current_thresholds= CurrentPlaneThresholds(
            gear=gear_thresh,
            frame=frame_thresh,
            frame_mach=frame_mach_thresh,
            flaps=flap_thresholds
        )

    def _get_safe_flap_state(self) -> str:
        """Determine the safe flap state based on the current speed and thresholds."""
        assert self._current_thresholds is not None, "Current thresholds should not be None when determining safe flap state."
        if self._plane is None:
            raise ValueError("No current plane to determine safe flap state for.")
        
        current_speed = self._plane.telemetry.ias
        
        for flap_state in self._plane.flaps.possible[::-1]:  # Check from most deployed to least
            if flap_state.name == FlapState.NONE:
                return FlapState.NONE.value
            if current_speed < self._current_thresholds.flaps.get(flap_state.name.value, SpeedThreshold(float('inf'), self._warning_settings)).warning_speed:
                return flap_state.name.value
        return FlapState.NONE.value  # Default to NONE if no other state is safe
    
    def __get_safe_flap_state(self) -> FlapState:
        if self._current_thresholds is None or self._plane is None:
            return FlapState.NONE
        
        thresholds = [(key,value) for key, value in self._current_thresholds.flaps.items()]
        thresholds.sort(key= lambda x: x[1].fatal_speed)  # Sort by fatal speed ascending
        current_speed = self._plane.telemetry.ias
        
        for flap_thresh in thresholds:
            state, speed_threshold = flap_thresh
            if current_speed < speed_threshold.fatal_speed:
                return FlapState.from_str(state)
        return FlapState.NONE
                
            
    def __get_current_flap_state(self) -> FlapState:
        if self._plane is None:
            return FlapState.NONE
        for state in self._plane.flaps.possible[::-1]:
            if state.min_perc <= self._plane.telemetry.flaps.current:
                return state.name
        
        return FlapState.NONE
    
def _get_threshold_value(max_speed: int | float, warning_settings: WarningSettings, speed_in_mach: bool = False) -> float | int:
    """Calculate a single warning threshold for a max speed, based on the given WarningSettings."""

    if speed_in_mach:
        calc_tresh = max_speed * (warning_settings.mach_threshold / 100.0)
        max_tresh = max_speed - warning_settings.min_mach_diff
        min_tresh = max_speed - warning_settings.max_mach_diff
    else:
        calc_tresh = max_speed * (warning_settings.speed_treshold / 100.0)
        max_tresh = max_speed - warning_settings.min_diff
        min_tresh = max_speed - warning_settings.max_diff

    if calc_tresh > max_tresh:
        result = max_tresh
    elif calc_tresh < min_tresh:
        result = min_tresh
    else:
        result = calc_tresh

    if not speed_in_mach:
        result = int(result)
    return result