from tinydb import TinyDB, Query
from paths import SETTINGS_PATH
from PySide6.QtCore import QByteArray
entry = Query()

INTERNAL_NAMES = ["global_settings", "layout", "dicts"]
class LocalDB(object):
    def __init__(self):
        self.db = TinyDB(SETTINGS_PATH)
        
        
    def get_layout(self, name: str = "main_layout") -> QByteArray | None:
        """Get the layout state stored in the current Users directory.

        Args:
            name (str, optional): The name of the layout. Defaults to "main_layout".

        Returns:
            QByteArray|None: The layout state as QByteArray. None if nothing was saved
        """
        assert isinstance(name, str)

        layout_entry = self.db.table("layout").get(entry.id == name)
        if layout_entry is not None:
            hex_str = layout_entry["value"]
            return QByteArray.fromHex(hex_str.encode())
        return None
    
    def save_layout(self, layout: QByteArray, name:str = "main_layout") -> None:
        """Save a bytes Object representing the Layout for later use.

        Args:
            layout (bytes): The layout to save.
            name (str): The name of the layout, defaults to "main_layout".        
        """
        assert isinstance(layout, QByteArray)
        assert isinstance(name, str)
        
        self.db.table("layout").upsert(
            {
                "id": name,
                "value": layout.toHex().data().decode()
            }, 
            entry.id == name
        )
        
    def save_global_settings(self, settings:dict):
        """Save the global settings in the local database.

        Args:
            settings (dict): The settings to save.
        """
        assert isinstance(settings, dict)
        
        self.__save_dict(settings, "global_settings")
    
    def get_global_settings(self) -> dict:
        """Get the global settings from the local database.

        Returns:
            dict: The global settings.
        """
        return self.__get_dict("global_settings", {})
    
    def save_dict(self, dictionary:dict, name:str):
        """Save an object as dict in the local database.

        Args:
            dictionary (dict): The dictionary to save.
            name (str): The name of the dictionary.
        """
        assert isinstance(dictionary, dict)
        assert isinstance(name, str)
        assert name not in INTERNAL_NAMES, "Name is reserved for internal use"
        
        self.__save_dict(dictionary, name)
    
    def get_dict(self, name:str, default:dict= {}) -> dict:
        """Get an object from the local database.

        Args:
            name (str): The name of the dictionary.
        """
        assert isinstance(name, str)
        assert name not in INTERNAL_NAMES, "Name is reserved for internal use"
        
        return self.__get_dict(name, default)
    
    def __save_dict(self, dictionary:dict, name:str):
        """Save an object as dict in the local database.

        Args:
            dictionary (dict): The dictionary to save.
            name (str): The name of the dictionary.
        """
        assert isinstance(dictionary, dict)
        assert isinstance(name, str)
        
        self.db.table("dicts").upsert(
            {
                "id": name,
                "value": dictionary
            }, 
            entry.id == name
        )
    
    def __get_dict(self, name:str, default:dict= {}) -> dict:
        """Get an object from the local database.

        Args:
            name (str): The name of the dictionary.

        Returns:
            dict: The object as dictionary.
        """
        assert isinstance(name, str)
        
        dictionary = self.db.table("dicts").get(entry.id == name)
        if dictionary is not None:
            return dictionary.get("value")
        else:
            return default
        
    def add_or_update_value(self, dict_name:str, key:str, value):
        """Add or update an entry in a local database object.

        Args:
            dict_name (str): The name of the dictionary.
            key (str): The key of the entry.
            value: The value of the entry.
        """
        assert isinstance(dict_name, str)
        assert isinstance(key, str)
        assert self.db.table("dicts").contains(entry.id == dict_name), "Dictionary does not exist"

        obj = self.db.table("dicts").get(entry.id == dict_name)
        obj["value"][key] = value
        self.db.table("dicts").upsert(obj, entry.id == dict_name)
        
    def get_value(self, dict_name:str, key:str):
        """Get an entry from a local database object.

        Args:
            dict_name (str): The name of the directory to get the Value from.
            key (str): The key of the value to retrive.  
        
        Raises:
            AssertionError: If the dictionary does not exist.
            AssertionError: If the value does not exist.
        
        Returns:
            The value of the entry.
        """
        assert isinstance(dict_name, str)
        assert isinstance(key, str)
        assert self.db.table("dicts").contains(entry.id == dict_name), "Dictionary does not exist"
        
        val = self.db.table("dicts").get(entry.id == dict_name)["value"][key]
        
        assert val is not None, "Value does not exist"
        return val