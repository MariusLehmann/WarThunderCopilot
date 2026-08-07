from PySide6.QtCore import QObject, Signal
from Packages.Models.Plane import Plane
from backend.oldSoundEngine import Sound
from backend.oldSoundEngine.sounds import SpeedWarningSound, FlapSpeedWarningSound, GearSpeedWarningSound, FlapInfoSound
from backend.telemetry_fetcher import TelemetryData
from backend.settings import WarningSettings
from wt_dataclasses import FlapState


class PlaneSpeedWarningEngine(QObject):
    _warning_settings:WarningSettings
    _current_plane:Plane|None
    _current_warnings:list[Sound] = []
    _informed_flap_state: FlapState = FlapState.NONE
    # SIGNALS
    play_sound_signal = Signal(list)
    stop_sound_signal = Signal(list)

    def __init__(self, warning_settings:WarningSettings|None = None):
        super().__init__()
        self._current_plane = None
        self._warning_settings = warning_settings if warning_settings is not None else WarningSettings()


    def on_new_plane(self, plane:Plane):
        """Update plane data and recalculate its warning thresholds.

        :param plane: the New Plane object
        :type plane: Plane
        """
        self._current_plane = plane
        plane.recalculate_thresholds(self._warning_settings)

    def on_new_telemetry(self, telemetry:TelemetryData):
        """Update telemetry data and recalculate warnings

        :param telemetry: the New Telemetry data
        :type telemetry: TelemetryData
        """
        warning_list:list[Sound] = []
        if telemetry is None or self._current_plane is None or self._current_plane.thresholds is None:
            return
        thresholds = self._current_plane.thresholds
        print(f"IAS: {telemetry.ias} | FLAPS: {telemetry.flaps} | GEAR: {telemetry.gear} | MACH: {telemetry.mach_speed} | TRESHOLDS: {thresholds}")

        if telemetry.ias is not None:
            if (telemetry.ias > thresholds.frame): #or (thresholds.frame_mach is not None and telemetry.mach_speed is not None and telemetry.mach_speed > thresholds.frame_mach):
                warning_list.append(SpeedWarningSound())
            if thresholds.frame_mach is not None and telemetry.mach_speed is not None and telemetry.mach_speed > thresholds.frame_mach:
                warning_list.append(SpeedWarningSound())

            if telemetry.ias > thresholds.gear and telemetry.gear > 0:
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
        """Update Threshold settings and recalculate the current plane's thresholds.

        :param settings: New Settings for the speed treshold calculation
        :type settings: WarningSettings
        """
        self._warning_settings = settings
        if self._current_plane is not None:
            self._current_plane.recalculate_thresholds(self._warning_settings)

    def _get_current_flap_state(self, current_flap_percentage:int) -> FlapState:
        """Get the current flap state based on the current flap deployment percentage

        :param current_flap_percentage: Current flap deployment in percentage
        :type current_flap_percentage: int
        :return: Current flap state
        :rtype: FlapState
        """
        if self._current_plane is None:
            return FlapState.NONE
        flap_states = self._current_plane.get_flap_deployment_thresholds()
        applicable_states = [state for state in flap_states if current_flap_percentage <= state[0]]
        if not applicable_states:
            return FlapState.NONE
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
        if self._current_plane is None or self._current_plane.thresholds is None:
            return None
        current_state = self._get_current_flap_state(current_flap_percentage)

        match current_state:
            case FlapState.COMBAT:
                return self._current_plane.thresholds.combat_flap
            case FlapState.START:
                return self._current_plane.thresholds.start_flap
            case FlapState.LANDING:
                return self._current_plane.thresholds.landing_flap
            case _:
                return None

    def _new_flap_avaliable(self, current_speed:int, current_flap_percentage:int) -> bool:

        FLAP_STATES = [
            FlapState.NONE,
            FlapState.COMBAT,
            FlapState.START,
            FlapState.LANDING
        ]

        if self._current_plane is None or self._current_plane.max_speeds is None:
            return False

        flap_states = self._current_plane.get_flap_deployment_thresholds()
        max_speeds = self._current_plane.max_speeds

        safe_state = FlapState.NONE
        for tresh ,flap_state in flap_states[::-1]:
            if flap_state == FlapState.NONE:
                safe_state = FlapState.NONE
                break
            if current_speed < max_speeds.get(flap_state.value, 0):
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
