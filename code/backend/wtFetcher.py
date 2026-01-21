from dataclasses import dataclass
from Packages.WarThunder import telemetry, mapinfo
from paths import get_resource_path
import time
import json

TELEMETRY_INFORMATION = {
    "planetype": ["airframe"],
    "flaps": ["flapState", "flaps, %"],
    "gear": ["gearState", "gear, %"],
    "lat": ["lat"],
    "lon": ["lon"],
    "ias": ["IAS, km/h"],
    "airbrake": ["airbrake, %"],
    "mach_speed": ["mach", "M"]
}
OPTIONAL_TELEMETRY = [
    "airbrake",
    "lat",
    "lon", 
    "mach_speed"
]
class TelemetryNotFoundException(Exception):
    pass
class PlaneNotFoundException(Exception):
    pass

@dataclass
class TelemetryData:
    planetype:str
    flaps: int
    gear: int
    ias: int
    lat: float = 0
    lon: float = 0
    airbrake: int = 0
    mach_speed: float = 999.9
class WTUpdater(object):
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
                
                
            
   
    def __update_telemetry(self) -> None:
        if not self.tel_interface.basic_telemetry and not self.tel_interface.full_telemetry:
            raise PlaneNotFoundException("No Plane Found.")
        
        
        self.telemetry = self.__parse_telemetry(self.tel_interface.basic_telemetry, self.tel_interface.full_telemetry)
    
    def __parse_telemetry(self, source:dict, optional_source:dict|None = None) -> TelemetryData:
        """Parse needet data from the Source, try optional source if given and not found in main source.
        Needet Arguments are defined in TELEMETRY_INFORMATION and OPTIONAL_TELEMETRY.
        
        Args:
            source (dict): Dict containing the information to parse
            optional_source (dict,optional): Second dict for use if the First one doesn't contain needet data.
        
        Returns:
            dict: A Dict containing the parsed information, with the keys defined in TELEMETRY_INFORMATION.
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
            
        return TelemetryData(**result_dict)
        
            
    
    def get_plane_telemetry(self) -> TelemetryData|None:
        return self.telemetry
    
    
if __name__ == '__main__':
    updater = WTUpdater("192.168.0.40")
    while True:
        updater.fetch_data()
        print(updater.get_plane_telemetry())
        time.sleep(0.5)