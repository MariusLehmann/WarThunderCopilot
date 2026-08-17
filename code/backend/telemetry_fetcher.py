from dataclasses import dataclass
from Packages.WarThunder import telemetry, mapinfo
from paths import get_resource_path
import time
import json

from wt_dataclasses import CurrentFlapState, TelemetryData

@dataclass
class ParsedTelemetryData:
    planetype: str
    flapState: int
    flapsAim: int
    gear: int
    ias: int
    lat: float = 0
    lon: float = 0
    mach_speed: float = 999.9
    airbrake: int | None = None
    sweep_lever: int | None = None
    sweep_indicator: int | None = None
        
    def to_telemetry_data(self) -> TelemetryData:
        return TelemetryData(
            planetype=self.planetype,
            flaps=CurrentFlapState(aim=self.flapsAim, current=self.flapState),
            gear=self.gear,
            ias=self.ias,
            lat=self.lat,
            lon=self.lon,
            airbrake=self.airbrake,
            mach_speed=self.mach_speed,
            wing_sweep_lever=self.sweep_lever,
            wing_sweep_indicator=self.sweep_indicator
        )
    
TELEMETRY_INFORMATION = {
    "planetype": ["airframe"],
    "flapState": ["flaps, %", "flapState"],
    "flapsAim": ["flaps"],
    "gear": ["gear, %", "gearState"],
    "lat": ["lat"],
    "lon": ["lon"],
    "ias": ["IAS, km/h"],
    "airbrake": ["airbrake, %"],
    "mach_speed": ["mach", "M"],
    "sweep_lever": ["wing_sweep_lever"],
    "sweep_indicator": ["wing_sweep_indicator"]
}
    
OPTIONAL_TELEMETRY = [
    "airbrake",
    "lat",
    "lon", 
    "mach_speed",
    "sweep_lever",
    "sweep_indicator"
]
class TelemetryNotFoundException(Exception):
    pass
class PlaneNotFoundException(Exception):
    pass


    
class TelemetryFetcher(object):
    def __init__(self, ip_addr, debug_mode=False):
        """Create an Fetcher to get Information from the WT-API
            If Debug Mode is enabled, information are fetched from a local json file instead of the API.
        Args:
            ip_addr (str): IP of the WT-API
            debug_mode (bool, optional): Debug-Mode, Defaults to False.
        """
        
        self.ip_addr = ip_addr
        self.debug_mode = debug_mode
        self.tel_interface = telemetry.TelemInterface(self.ip_addr)
        self.telemetry = None
        # self.map_info = mapinfo.MapInfo(self.ip_addr)
        
    def fetch_data(self) -> None:
        if not self.debug_mode:
            try:
                self.tel_interface.get_telemetry()
                self.__update_telemetry()
            except Exception as e:
                print(f"Error while fetching: {e}")
                
        else:
            with open(get_resource_path("debug-data.json"),"r") as file:
                data = json.load(file)
                
            self.telemetry = self.__parse_telemetry(data)
                
    def set_ip_addr(self, ip_addr:str) -> None:
        self.ip_addr = ip_addr
        self.tel_interface = telemetry.TelemInterface(self.ip_addr)
            
   
    def __update_telemetry(self) -> None:
        if not self.tel_interface.basic_telemetry and not self.tel_interface.full_telemetry:
            raise PlaneNotFoundException("No Plane Found.")
        
        
        self.telemetry = self.__parse_telemetry(self.tel_interface.basic_telemetry, self.tel_interface.full_telemetry)
    
    def __parse_telemetry(self, source:dict, optional_source:dict|None = None) -> ParsedTelemetryData:
        """Parse needet data from the Source, try optional source if given and not found in main source.
        Needet Arguments are defined in TELEMETRY_INFORMATION and OPTIONAL_TELEMETRY.
        
        Args:
            source (dict): Dict containing the information to parse
            optional_source (dict,optional): Second dict for use if the First one doesn't contain needet data.
        
        Returns:
            ParsedTelemetryData: An instance of ParsedTelemetryData containing the parsed information.
        """
        result_dict = {}
        
        for category, keys in TELEMETRY_INFORMATION.items():
            val = "--null--"
            
            for key in keys:
                val = source.get(key,"--null--")
                if val == "--null--" and optional_source:
                    val = optional_source.get(key,"--null--")
                
                if val != "--null--":
                    result_dict[category] = val
                    break
            
            if val == "--null--" and category not in OPTIONAL_TELEMETRY:
                raise TelemetryNotFoundException(f"Telemetry object {category} ({keys}) not found in Telemetry of the Plane.")
            
        return ParsedTelemetryData(**result_dict)
        
    def get_plane_telemetry(self) -> TelemetryData|None:
        if self.telemetry:
            return self.telemetry.to_telemetry_data()
        return None
    
    
if __name__ == '__main__':
    updater = TelemetryFetcher("192.168.0.40")
    while True:
        updater.fetch_data()
        print(updater.get_plane_telemetry())
        time.sleep(0.5)