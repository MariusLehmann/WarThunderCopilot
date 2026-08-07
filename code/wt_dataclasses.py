from dataclasses import dataclass
from enum import Enum

class FlapState(Enum):
    __state_order = ["none", "combat", "start", "landing"]
    
    NONE = "none"
    COMBAT = "combat"
    START = "start"
    LANDING = "landing"

    def __str__(self) -> str:
        return self.value
    
    def __gt__(self, state):
        if isinstance(state,FlapState):
            return self.__state_order.index(self.value) > self.__state_order.index(state.value)
        else:
            return False
        
    def __eq__(self, state):
        if isinstance(state,FlapState):
            return self.value == state.value
        else:
            return False
        
    @classmethod
    def from_str(cls, state_str:str) -> "FlapState":
        for state in cls:
            if state.value == state_str:
                return state
        raise ValueError(f"Invalid FlapState string: {state_str}")

@dataclass
class PossibleFlapState:
    name: FlapState
    min_perc: int
    
    def copy(self) -> "PossibleFlapState":
        return PossibleFlapState(name=self.name, min_perc=self.min_perc)
  

GENERAL_FLAP_STATES = [
    PossibleFlapState(name=FlapState.NONE, min_perc=0),
    PossibleFlapState(name=FlapState.COMBAT, min_perc=20),
    PossibleFlapState(name=FlapState.START, min_perc=50),
    PossibleFlapState(name=FlapState.LANDING, min_perc=100) 
    ]

@dataclass
class SpeedLimit:
    min_speed: float
    max_speed: float
    unit: str
    
@dataclass
class CurrentFlapState:
    aim: int
    current: int
    
@dataclass
class TelemetryData:
    planetype:str
    flaps: CurrentFlapState
    gear: int
    ias: int
    lat: float = 0
    lon: float = 0
    airbrake: int = 0
    mach_speed: float = 999.9
    wing_sweep_lever: int | None = None
    wing_sweep_indicator: int | None = None
    
@dataclass
class GeneralSpeedLimits:
    gear: SpeedLimit
    frame: SpeedLimit
    frame_mach:SpeedLimit
    
    combat_flap:None|int
    start_flap:None|int
    landing_flap:None|int
    
    def get_current_limits(self, wing_sweep:int | None) -> 'CurrentSpeedLimits':
        """Get the current max speeds for this plane.
            Those are the max speeds that are currently relevant, based on the current wing position.
        
        Args:
            wing_sweep (int): The current wing sweep position of the plane. (1 = fully swept, 0 = fully unswept)
        """
        # Calculate the current max speeds based on the wing sweep position sweep = 100: max, sweep = 0: min
        if wing_sweep is None:
            wing_sweep = 0
        
        current_gear = self.__calc_current(self.gear.min_speed, self.gear.max_speed, wing_sweep)
        current_frame = self.__calc_current(self.frame.min_speed, self.frame.max_speed, wing_sweep)
        current_frame_mach = self.__calc_current(self.frame_mach.min_speed, self.frame_mach.max_speed, wing_sweep)

        return CurrentSpeedLimits(
            gear=int(current_gear),
            frame=int(current_frame),
            frame_mach=round(float(current_frame_mach),3),
            combat_flap=self.combat_flap,
            start_flap=self.start_flap,
            landing_flap=self.landing_flap
        )
        
    @staticmethod
    def __calc_current(min, max, sweep):
        return min + (max - min) * sweep

@dataclass
class CurrentSpeedLimits: 
    gear: int
    frame: int
    frame_mach: float
    
    combat_flap: int|None
    start_flap: int|None
    landing_flap: int|None

@dataclass
class PlaneProperties:
    planetype: str
    planename: str
    
    speed_limits: GeneralSpeedLimits