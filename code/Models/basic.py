from enum import Enum



class Theme(Enum):
    AUTO = 0
    LIGHT = 1
    DARK = 2
    
    
THEME_NAMES = {
    Theme.LIGHT: "Hell",
    Theme.DARK: "Dunkel",
    Theme.AUTO: "Automatisch"
}