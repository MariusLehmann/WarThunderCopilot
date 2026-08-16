import copy

from dataclasses import dataclass, field
from Packages.connector import PlaneNotFound, BackendAPIConnection, APIConnectionError
from backend.telemetry_fetcher import TelemetryData
from backend.settings import WarningSettings
from enum import Enum

from wt_dataclasses import PlaneProperties, CurrentSpeedLimits, CurrentFlapState, PossibleFlapState, GENERAL_FLAP_STATES, FlapState

conn = BackendAPIConnection()

class PlaneFetchError(Exception):
    """Base class for exceptions in this module."""
    pass


@dataclass
class FlapProperties:
    possible: list[PossibleFlapState] = field(default_factory=lambda: [GENERAL_FLAP_STATES[0].copy()])
    
    def add_flap_state(self, flap_state:PossibleFlapState|str):
        """Add a new flap state to the list of possible flap states.
        The new flap state will be added in the correct order based on its min_perc value.

        Args:
            flap_state (PossibleFlapState|str): The flap state to add.
        """
        if isinstance(flap_state, str):
            new_flap_state = None
            for state in GENERAL_FLAP_STATES:
                if state.name.value == flap_state:
                    new_flap_state = state
                    break
            assert new_flap_state is not None, f"Flap state '{flap_state}' not found in GENERAL_FLAP_STATES."
                    
        else:
            new_flap_state = flap_state
        assert isinstance(new_flap_state, PossibleFlapState), "flap_state must be a PossibleFlapState or a valid flap state name string."
            
        if any(state.name == new_flap_state.name for state in self.possible):
            return  # Flap state already exists, do not add it again
        new_flap_state = new_flap_state.copy()  # Create a copy to avoid modifying the original
        
        # Insert the new flap state in the correct order based on min_perc
        for i, state in enumerate(self.possible):
            if new_flap_state.min_perc < state.min_perc:
                self.possible.insert(i, new_flap_state)
                return
        self.possible.append(new_flap_state)  # Add to the end if it's the largest min_perc
    
    def get_avaliable_bool(self) -> tuple[bool,bool,bool]:
        """Get a tuple describing which flaps are avaliable on this Plane

        Args:
            self (FlapProperties): The FlapProperties instance.
        
        Returns: 
            tuple[bool,bool,bool]: Tuple of bools in the Form (combat, start, landing)
        """
        return (
            any(state.name == "combat" for state in self.possible),
            any(state.name == "start" for state in self.possible),
            any(state.name == "landing" for state in self.possible)
        )

    def get_possible_flap_states(self) -> list[FlapState]:
        res = []
        for possible_state in self.possible:
            res.append(possible_state.name)

class Plane(object):
    telemetry:TelemetryData
    properties: PlaneProperties
    flaps:FlapProperties
    

    def __init__(self, telemetry:TelemetryData):
        self.telemetry = telemetry
        self.planetype = telemetry.planetype.lower()
        try:
            self.properties = conn.get_plane(self.planetype)
        except PlaneNotFound as e:
            raise PlaneFetchError(f"Plane {self.planetype} not found in DB") from e
        except APIConnectionError as e:
            raise PlaneFetchError(f"API connection error: {e}") from e
            
        self.flaps = FlapProperties()
        self.name = self.properties.planename
    
        # init possible flap states
        if self.properties.speed_limits.combat_flap is not None:
            self.flaps.add_flap_state("combat")
        if self.properties.speed_limits.start_flap is not None:
            self.flaps.add_flap_state("start")
        if self.properties.speed_limits.landing_flap is not None:
            self.flaps.add_flap_state("landing")

    def update_telemetry(self, telemetry:TelemetryData):
        """Update Flighttelemetry data of the plane.
        
        Args:
            telemetry (TelemetryData): The new flight-telemetry data
        """
        self.telemetry = telemetry

    def get_current_max_speeds(self) -> CurrentSpeedLimits:
        """Get the current max speeds for this plane.
            Those are the max speeds that are currently relevant, based on the current flap state.
        """
        return self.properties.speed_limits.get_current_limits(self.telemetry.wing_sweep_indicator)
    
    def copy(self) -> "Plane":
        """Creates a deep Copy of the Plane Object

        :return: new copied plane Object
        :rtype: Plane
        """
        new_plane = copy.deepcopy(self)
        return new_plane
    
    # def recalculate_thresholds(self, warning_settings:WarningSettings) -> CurrentSpeedLimits|None:
    #     """Recalculate the speed/mach warning thresholds for this plane and store them in self.thresholds.
    #     Should be called once after the plane is created and again whenever WarningSettings change.

    #     :param warning_settings: Settings controlling how close to the max speed a threshold is placed.
    #     :type warning_settings: WarningSettings
    #     :return: The calculated thresholds, or None if this plane has no known max speeds.
    #     :rtype: PlaneMaxSpeeds|None
    #     """
    #     gear_tresh = _get_threshold_value(self.max_speeds["gear"], warning_settings)
    #     frame_tresh = _get_threshold_value(self.max_speeds["frame"], warning_settings)
    #     frame_mach_tresh = _get_threshold_value(self.max_speeds.get("frame mach", None), warning_settings, speed_in_mach=True)
    #     combat_tresh = _get_threshold_value(self.max_speeds.get("combat", None), warning_settings)
    #     start_tresh = _get_threshold_value(self.max_speeds.get("start", None), warning_settings)
    #     landing_tresh = _get_threshold_value(self.max_speeds.get("landing", None), warning_settings)

    #     assert isinstance(gear_tresh, int)
    #     assert isinstance(frame_tresh, int)
    #     assert isinstance(frame_mach_tresh, float) or frame_mach_tresh is None
    #     self.thresholds = PlaneMaxSpeeds(
    #         gear=gear_tresh,
    #         frame=frame_tresh,
    #         frame_mach=frame_mach_tresh,
    #         combat_flap=int(combat_tresh) if combat_tresh is not None else None,
    #         start_flap=int(start_tresh) if start_tresh is not None else None,
    #         landing_flap=int(landing_tresh) if landing_tresh is not None else None
    #     )
    #     return self.thresholds

    # def get_flaps_avaliable(self) -> tuple[bool,bool,bool]:
    #     """Get an tuple describing which flaps are avaliable on this Plane

    #     :return: Tuple of bools in the Form (combat, start, landing)
    #     :rtype: tuple[bool]
    #     """
    #     return self.flaps_avaliable

    # def get_safe_flap_state(self) -> str:
    #     """Get String representing the current safe usable flap state

    #     Returns:
    #         str: Flap state (one of ["none", "combat", "start", "landing"])

    #     """

    #     ias = self.telemetry.ias if self.telemetry is not None else None
    #     if ias is None:
    #         return "none"

    #     for state in self.possible_flaps[::-1]:
    #         if state["name"] == "none":
    #             return "none"
    #         if ias < self.max_speeds[state["name"]]:
    #             return state["name"]
    #     return "none"
    # TODO: alles darunter noch übertragen  
    # def get_max_speeds(self) -> dict|None:
    #     """Get a dict containing the max speeds of this plane

    #     :return: Dict in the form {"gear":int,"frame":int,"combat":int|None,"start":int|None,"landing":int|None} None if no Plane is avaliable
    #     :rtype: dict|None
    #     """
    #     if not self.max_values_avaliable:
    #         return None
    #     return self.max_speeds

    # def get_flap_deployment_thresholds(self) -> list[tuple[int,FlapState]]:
    #     """Get a list of tuples containing Deployment thresholds for flap states.
    #     Each tuple contains (speed:int, flap_state:FlapState)
    #     if current flap deployment is bigger than the given percentage, the corrosponding state applies.

    #     :return: List of Deployment thresholds
    #     :rtype: list[tuple[int,FlapState]]
    #     """
    #     thresholds = []
    #     for state in self.possible_flaps:
    #         match state["name"]:
    #             case "none":
    #                 thresholds.append( (0, FlapState.NONE) )
    #             case "combat":
    #                 thresholds.append( (state["perc"], FlapState.COMBAT) )
    #             case "start":
    #                 thresholds.append( (state["perc"], FlapState.START) )
    #             case "landing":
    #                 thresholds.append( (state["perc"], FlapState.LANDING) )
    #     return thresholds



# class OldPlane(object):
#     telemetry:TelemetryData
#     properties: PlaneProperties
    
#     thresholds:PlaneMaxSpeeds|None
#     possible_flaps:list[PossibleFlapState]
#     flaps_avaliable:tuple[bool,bool,bool]

#     informed_flap_state:str

#     def __init__(self, plane_type:str):
#         self.planetype = plane_type.lower()
#         self.properties = conn.get_plane(self.planetype)

#         self.name = self.properties.planename


#         self.possible_flaps = GENERAL_FLAP_STATES.copy()[:1] # Start with only the "none" flap state
#         self.thresholds = None
        
#         self.max_speeds = {
#             "gear": self.properties.gear_max,
#             "frame": self.properties.frame_max,
#             "frame mach": self.properties.mach_limit,
#             "combat": self.properties.combat_max,
#             "start": self.properties.start_max,
#             "landing": self.properties.landing_max
#         }
        
#         ## TODO ab hier weiter Überarbeiten (max speeds haben sich geändert, es gibt neue Typen)
        
#         for key,value in self.max_speeds.items():
#             if value == '' or value is None:
#                 self.max_speeds[key] = None
#             elif key == "frame mach":
#                 self.max_speeds[key] = float(value)
#             else:
#                 self.max_speeds[key] = int(value)

#         self.flaps_avaliable = (
#             (self.max_speeds["combat"] != '') and (self.max_speeds["combat"] is not None),
#             (self.max_speeds["start"] != '') and (self.max_speeds["start"] is not None),
#             (self.max_speeds["landing"] != '') and (self.max_speeds["landing"] is not None)
#         )


#         for i in range(len(GENERAL_FLAP_STATES)):
#             if self.flaps_avaliable[i]:
#                 self.possible_flaps.append(GENERAL_FLAP_STATES[i])
#         self.possible_flaps[-1]["perc"] = 100

        


#         self.telemetry = None

#         self.informed_flap_state = "none"

#     def set_telemetry(self, telemetry:TelemetryData):
#         self.telemetry = telemetry

#     def recalculate_thresholds(self, warning_settings:WarningSettings) -> PlaneMaxSpeeds|None:
#         """Recalculate the speed/mach warning thresholds for this plane and store them in self.thresholds.
#         Should be called once after the plane is created and again whenever WarningSettings change.

#         :param warning_settings: Settings controlling how close to the max speed a threshold is placed.
#         :type warning_settings: WarningSettings
#         :return: The calculated thresholds, or None if this plane has no known max speeds.
#         :rtype: PlaneThresholds|None
#         """
#         gear_tresh = _get_threshold_value(self.max_speeds["gear"], warning_settings)
#         frame_tresh = _get_threshold_value(self.max_speeds["frame"], warning_settings)
#         frame_mach_tresh = _get_threshold_value(self.max_speeds.get("frame mach", None), warning_settings, speed_in_mach=True)
#         combat_tresh = _get_threshold_value(self.max_speeds.get("combat", None), warning_settings)
#         start_tresh = _get_threshold_value(self.max_speeds.get("start", None), warning_settings)
#         landing_tresh = _get_threshold_value(self.max_speeds.get("landing", None), warning_settings)

#         assert isinstance(gear_tresh, int)
#         assert isinstance(frame_tresh, int)
#         assert isinstance(frame_mach_tresh, float) or frame_mach_tresh is None
#         self.thresholds = PlaneMaxSpeeds(
#             gear=gear_tresh,
#             frame=frame_tresh,
#             frame_mach=frame_mach_tresh,
#             combat_flap=int(combat_tresh) if combat_tresh is not None else None,
#             start_flap=int(start_tresh) if start_tresh is not None else None,
#             landing_flap=int(landing_tresh) if landing_tresh is not None else None
#         )
#         return self.thresholds

#     def get_flaps_avaliable(self) -> tuple[bool,bool,bool]:
#         """Get an tuple describing which flaps are avaliable on this Plane

#         :return: Tuple of bools in the Form (combat, start, landing)
#         :rtype: tuple[bool]
#         """
#         return self.flaps_avaliable

#     def get_safe_flap_state(self) -> str:
#         """Get String representing the current safe usable flap state

#         Returns:
#             str: Flap state (one of ["none", "combat", "start", "landing"])

#         """

#         ias = self.telemetry.ias if self.telemetry is not None else None
#         if ias is None:
#             return "none"

#         for state in self.possible_flaps[::-1]:
#             if state["name"] == "none":
#                 return "none"
#             if ias < self.max_speeds[state["name"]]:
#                 return state["name"]
#         return "none"

#     def get_max_speeds(self) -> dict|None:
#         """Get a dict containing the max speeds of this plane

#         :return: Dict in the form {"gear":int,"frame":int,"combat":int|None,"start":int|None,"landing":int|None} None if no Plane is avaliable
#         :rtype: dict|None
#         """
#         if not self.max_values_avaliable:
#             return None
#         return self.max_speeds

#     def get_flap_deployment_thresholds(self) -> list[tuple[int,FlapState]]:
#         """Get a list of tuples containing Deployment thresholds for flap states.
#         Each tuple contains (speed:int, flap_state:FlapState)
#         if current flap deployment is bigger than the given percentage, the corrosponding state applies.

#         :return: List of Deployment thresholds
#         :rtype: list[tuple[int,FlapState]]
#         """
#         thresholds = []
#         for state in self.possible_flaps:
#             match state["name"]:
#                 case "none":
#                     thresholds.append( (0, FlapState.NONE) )
#                 case "combat":
#                     thresholds.append( (state["perc"], FlapState.COMBAT) )
#                 case "start":
#                     thresholds.append( (state["perc"], FlapState.START) )
#                 case "landing":
#                     thresholds.append( (state["perc"], FlapState.LANDING) )
#         return thresholds

if __name__ == '__main__':
    plane = Plane(TelemetryData(planetype="f-86f", flaps=CurrentFlapState(0,0), gear=0, ias=500, lat=0, lon=0, airbrake=0, mach_speed=0.8, wing_sweep_lever=None, wing_sweep_indicator=None))
