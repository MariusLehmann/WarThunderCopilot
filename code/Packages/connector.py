from dataclasses import dataclass
import requests
from wt_dataclasses import SpeedLimit, PlaneProperties, GeneralSpeedLimits
  
@dataclass
class APIReturnedPlane:
    planetype: str
    planename: str
    frame_max: SpeedLimit
    gear_max: SpeedLimit
    combat_max: int | None
    start_max: int | None
    landing_max: int | None
    mach_limit: SpeedLimit
    
    def __post_init__(self):
        # Ensure that the speed limits are instances of SpeedLimit
        if not isinstance(self.frame_max, SpeedLimit):
            self.frame_max = SpeedLimit(**self.frame_max)
        if not isinstance(self.gear_max, SpeedLimit):
            self.gear_max = SpeedLimit(**self.gear_max)
        if not isinstance(self.mach_limit, SpeedLimit):
            self.mach_limit = SpeedLimit(**self.mach_limit)
    
    def to_plane_properties(self) -> PlaneProperties:
        return PlaneProperties(
            planetype=self.planetype,
            planename=self.planename,
            speed_limits=GeneralSpeedLimits(
                gear=self.gear_max,
                frame=self.frame_max,
                frame_mach=self.mach_limit,
                combat_flap=self.combat_max,
                start_flap=self.start_max,
                landing_flap=self.landing_max
            )
        )

class PlaneNotFound(Exception):
    def __init__(self, plane_type):
        self.plane_type = plane_type
        super().__init__(f"Plane {plane_type} not found in DB")

class APIConnectionError(ConnectionError):
    pass

class BackendAPIConnection: 
    def __init__(self, base_url="https://api.wtc.mariuslehmann.de/wtc/plane/"):
        self.base_url = base_url
        
    def get_plane(self, plane_type: str) -> PlaneProperties:
        response = requests.get(f"{self.base_url}{plane_type}")
        try:
            response.raise_for_status()  # Raise an exception for bad status codes
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise PlaneNotFound(plane_type) from e
            else:
                raise APIConnectionError(f"API error: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Network error: {e}") from e
        
        data = response.json()
        
        plane = APIReturnedPlane(**data)
        
        return plane.to_plane_properties()

@dataclass
class DBPlane:
    name: str
    key: str
    gear_max_speed: int
    frame_max_speed: int
    mach_limit:float
    combat_flap_speed: int|None = None
    start_flap_speed: int|None = None
    landing_flap_speed: int|None = None
    
    start_speed: int|None = None
    landing_speed: int|None = None

class APIConnection:
    """Connector for the Jarvis-API
    """
    def __init__(self):
        """Create connector for the Jarvis-API
        """
        self.base_url = "https://api.jarvis.mariuslehmann.de/wtc/plane/"
        
    def get_plane(self, plane_id:str) -> DBPlane:
        """Fetch a Planes Data from the Database. If the Plane does not Exist yet, the API will try to fetch informations from the Warthunder Wiki.
        

        :param plane_id: ID of the Plane to fetch
        :type plane_id: str
        :raises PlaneNotFound: If the Plane does not Exist and could net be fetched, or other errors Occured while fetching
        :raises APIConnectionError: If the Connetion to the API fails
        :return: Plane Data
        :rtype: DBPlane
        """
        response = requests.get(f"{self.base_url}{plane_id}")
        try:
            response.raise_for_status() # Raise an exception for bad status codes
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise PlaneNotFound(plane_id) from e
            else:
                raise APIConnectionError(f"API error: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Network error: {e}") from e
        data = response.json()
        
        plane = DBPlane(
            name = data["planename"],
            key = data["planetype"],
            gear_max_speed = data["gear_max"],
            frame_max_speed = data["frame_max"],
            mach_limit= data["mach_limit"],
            combat_flap_speed = data.get("combat_max"),
            start_flap_speed = data.get("start_max"),
            landing_flap_speed = data.get("landing_max"),
            # Startspeed und Landingspeed unterstützt die API noch nicht
        )
        return plane
        
        
if __name__ == "__main__":
    conn = APIConnection()
    print(conn.get_plane("b-29"))
    
