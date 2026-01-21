import darkdetect
import qdarktheme


class SettingsCollection:
    ip:str
    intervall:int
    theme:str
    theme_was_auto:bool = False
    
    speed_warning_treshold:float
    speed_warning_min_diff:int
    speed_warning_max_diff:int
    
    def __init__(self, ip:str, intervall:int, theme:str, speed_warning_treshold:float = 90, speed_warning_min_diff:int = 10, speed_warning_max_diff:int = 50):
        """Create and Validate an instance of SettingsCollection.
        
        Args:
            ip (str): The ip to fetch the WT information from
            intervall (int): the Fetching intervall
            theme (str): The theme of the Window (has to be one of "Automatisch", "Hell", "Dunkel")
            
        Raises:
            ValueError: if one of the inputs is not valid
        """
        if not self.__is_valid_ip(ip):
            raise ValueError("Invalid IP address provided.")
        if theme not in ["Automatisch", "Hell", "Dunkel"]:
            raise ValueError("Invalid theme provided. Must be 'Automatisch', 'Hell', or 'Dunkel'.")
        if not isinstance(intervall, int):
            raise ValueError("Invalid intervall provided. Must be an integer.")
        
        self.ip = ip
        self.intervall = intervall
        self.set_theme(theme)
        
        self.speed_warning_treshold = speed_warning_treshold
        self.speed_warning_min_diff = speed_warning_min_diff
        self.speed_warning_max_diff = speed_warning_max_diff
        

    def __is_valid_ip(self, ip: str) -> bool:
        """Check if the provided IP address is valid.
        
        Args:
            ip (str): The IP address to check.
            """
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
        
    def set_theme(self,theme:str, autoapply:bool = False) -> None:
        """Set the theme to "Hell" or "Dunkel", depending on which option is Providet. Also resolve "Automatisch" Selection.
        
        Args:
            theme (str): The theme to set.
            autoapply (bool): If true , the set themewill be applied immediately, defaults to False.
            
        Raises:
            AssertionError: If the theme is not valid.
        """
        
        assert theme in ["Automatisch", "Hell", "Dunkel"]
        
        if theme == "Automatisch":
            self.theme_was_auto = True
            theme = darkdetect.theme().lower()
            if theme == "dark":
                self.theme = "Dunkel"
            else:
                self.theme = "Hell"
        else:
            self.theme_was_auto = False
            self.theme = theme
        
        if autoapply:
            self.apply_theme()
        
    
    def apply_theme(self) -> None:
        """Apply the selected Theme to the Window."""
        assert self.theme in ["Hell", "Dunkel"]
        if self.theme == "Hell":
            qdarktheme.setup_theme("light")
        elif self.theme == "Dunkel":
            qdarktheme.setup_theme("dark")
        
    def to_dict(self) -> dict:
        """Export the SettingsCollection to a dictionary.

        Returns:
            dict: A dictionary representation of the settings.
        """
        return {
            "ip": self.ip,
            "intervall": self.intervall,
            "theme": "Automatisch" if self.theme_was_auto else self.theme,
            "speed_treshold": self.speed_warning_treshold,
            "min_diff": self.speed_warning_min_diff,
            "max_diff": self.speed_warning_max_diff
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create a SettingsCollection instance from a dictionary.

        Args:
            data (dict): A dictionary containing the settings.

        Returns:
            SettingsCollection: An instance of SettingsCollection.
        """
        theme = data.get("theme", "Automatisch")
        instance = cls(data.get("ip", ""), data.get("intervall", 1000), theme, data.get("speed_treshold", 90), data.get("min_diff", 10), data.get("max_diff", 50))
        if theme == "Automatisch":
            instance.theme_was_auto = True
        return instance
