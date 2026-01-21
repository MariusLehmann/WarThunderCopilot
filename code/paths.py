import sys
import os
from pathlib import Path
import shutil
import json

APP_NAME = "WT_Copilot"

def get_user_data_dir() -> Path:
    """
    Ermittelt das Benutzerverzeichnis für die App.
    Windows: %LOCALAPPDATA%/WT_Copilot
    Mac/Linux: ~/WT_Copilot
    """  
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'): # Wenn die Anwendung als gebündelte ausführbare Datei läuft (PyInstaller)
        user_dir = Path(os.getenv("LOCALAPPDATA", Path.home()))
        data_dir = user_dir / APP_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        
        return data_dir
    else: # Andernfalls (Entwicklungsmodus oder normale Python-Ausführung)
        return Path(__file__).resolve().parent.parent

def get_resource_path(relative_path: str) -> Path:
    """
    Retrive the full Path to a ressource for dev and live use.
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller temporärer Pfad
        base_path = Path(sys._MEIPASS)
    else:
        # Entwicklungsmodus: Pfad relativ zu project/code/
        base_path = Path(__file__).resolve().parent.parent
    return base_path / relative_path

def initialize_user_data():
    """
    Erstinitialisierung der Settings und Sounds im Benutzerverzeichnis
    """
    user_dir = get_user_data_dir()

    # --- settings.json ---
    settings_path = user_dir / "settings.json"
    if not settings_path.exists():
        default_settings = {} # Default values for each Setting are hard coded in the modules using them
        settings_path.write_text(json.dumps(default_settings, indent=2), encoding="utf-8")
    
    # -------- Sound Paths --------
    sound_base = user_dir / "sounds"
    if not sound_base.exists():
        sound_base.mkdir(parents=True, exist_ok=True)
    
    # --- sounds/buildin/ ---
    sounds_dir = sound_base / "buildin"
    source_sounds = get_resource_path("sounds/buildin")
    if source_sounds.exists():
        if str(source_sounds) != str(sounds_dir):
            shutil.copytree(source_sounds, sounds_dir, dirs_exist_ok=True)

    # --- sounds/custom/ ---
    user_sounds_dir = sound_base / "custom"
    user_sounds_dir.mkdir(parents=True, exist_ok=True)
    
    # --- logging path ---
    log_dir = user_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    return settings_path, sounds_dir, user_sounds_dir, log_dir

# --- global path Variables  ---
USER_DIR = get_user_data_dir()
SETTINGS_PATH, SOUNDS_DIR, USER_SOUNDS_DIR, LOG_PATH = initialize_user_data()
