from Packages.connector import PlaneNotFound, DBPlane, APIConnection
from Packages.local_db import LocalDB
from backend.wtFetcher import TelemetryData
from enum import Enum


conn = APIConnection()
db = LocalDB()
GENERAL_FLAP_STATES = [
    {"name": "combat", "perc": 25}, 
    {"name": "start", "perc": 50},
    {"name": "landing", "perc": 100}
    ]
class flapState(Enum):
    NONE = "none"
    COMBAT = "combat"
    START = "start"
    LANDING = "landing"

    def __str__(self) -> str:
        return self.value
    
class WTPlane(object):
    telemetry:TelemetryData|None
    max_speeds:dict
    recommended_speeds:dict
    max_values_avaliable:bool
    
    possible_flaps:list[dict]
    flaps_avaliable:tuple[bool,bool,bool]
    
    informed_flap_state:str
    
    def __init__(self, plane_type:str ,friendly:bool = True, ):
        self.friendly = friendly
        self.planetype = plane_type.lower()
        
        self.possible_flaps = [{"name":"none","perc":0}]
        try:
            self.db_data:DBPlane = conn.get_plane(self.planetype)
            self.name = self.db_data.name
            self.max_values_avaliable = True
            
            self.max_speeds = {
                "gear": self.db_data.gear_max_speed,
                "frame": self.db_data.frame_max_speed,
                "frame mach": self.db_data.mach_limit,
                "combat": self.db_data.combat_flap_speed,
                "start": self.db_data.start_flap_speed,
                "landing": self.db_data.landing_flap_speed
            }
            for key,value in self.max_speeds.items():
                if value == '' or value is None:
                    self.max_speeds[key] = None
                elif key == "frame mach":
                    self.max_speeds[key] = float(value)
                else:
                    self.max_speeds[key] = int(value)
            
            self.recommended_speeds = {
                "start": self.db_data.start_speed,
                "landing": self.db_data.landing_speed
            }
            self.flaps_avaliable = (
                (self.max_speeds["combat"] != '') and (self.max_speeds["combat"] is not None),
                (self.max_speeds["start"] != '') and (self.max_speeds["start"] is not None),
                (self.max_speeds["landing"] != '') and (self.max_speeds["landing"] is not None)
            )
            
            
            for i in range(len(GENERAL_FLAP_STATES)):
                if self.flaps_avaliable[i]:
                    self.possible_flaps.append(GENERAL_FLAP_STATES[i])           
            self.possible_flaps[-1]["perc"] = 100
            
            global_thesholds = db.get_dict("speed_warning_limits", default={})
            if global_thesholds:
                global_thesholds = {str(key):float(value) for key,value in global_thesholds.items()}
                
        except PlaneNotFound:
            self.max_values_avaliable = False
            self.name = plane_type
            
            self.max_speeds = {}
            self.recommended_speeds = {}
            self.flaps_avaliable = (False, False, False)
        
        

        self.telemetry = None
        
        self.informed_flap_state = "none"
    
    def set_telemetry(self, telemetry:TelemetryData):
        self.telemetry = telemetry
    
    def get_flaps_avaliable(self) -> tuple[bool,bool,bool]:
        """Get an tuple describing which flaps are avaliable on this Plane

        :return: Tuple of bools in the Form (combat, start, landing)
        :rtype: tuple[bool]
        """
        return self.flaps_avaliable
    
    def get_safe_flap_state(self) -> str:
        """Get String representing the current safe usable flap state
        
        Returns:
            str: Flap state (one of ["none", "combat", "start", "landing"])
        
        """
        
        if not self.max_values_avaliable:
            return "none"
        
        ias = self.telemetry.ias if self.telemetry is not None else None
        if ias is None:
            return "none"
        
        for state in self.possible_flaps[::-1]:
            if state["name"] == "none":
                return "none"
            if ias < self.max_speeds[state["name"]]:
                return state["name"]
        return "none"        
    
    def get_max_speeds(self) -> dict|None:
        """Get a dict containing the max speeds of this plane

        :return: Dict in the form {"gear":int,"frame":int,"combat":int|None,"start":int|None,"landing":int|None} None if no Plane is avaliable
        :rtype: dict|None
        """
        if not self.max_values_avaliable:
            return None
        return self.max_speeds
    
    def get_flap_deployment_thresholds(self) -> list[tuple[int,flapState]]:
        """Get a list of tuples containing Deployment thresholds for flap states. 
        Each tuple contains (speed:int, flapState:flapState)
        if current flap deployment is bigger than the given percentage, the corrosponding state applies.
        
        :return: List of Deployment thresholds
        :rtype: list[tuple[int,flapState]]
        """
        thresholds = []
        for state in self.possible_flaps:
            match state["name"]:
                case "none":
                    thresholds.append( (0, flapState.NONE) )
                case "combat":
                    thresholds.append( (state["perc"], flapState.COMBAT) )
                case "start":
                    thresholds.append( (state["perc"], flapState.START) )
                case "landing":
                    thresholds.append( (state["perc"], flapState.LANDING) )
        return thresholds
    
if __name__ == '__main__':
    plane = WTPlane("f-80a")