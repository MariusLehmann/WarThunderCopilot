from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow


import time 
            
def main():
    app = QApplication([])
    app.setWindowIcon(QIcon("icon.ico"))

    main_window = MainWindow()
    main_window.show()
    app.exec()
    

def test():
    from Models import Plane
    from backend.telemetry_fetcher import TelemetryFetcher
    
    from backend.SoundEngine import SoundEngine, WT_Sound
    
    
    sound_engine = SoundEngine()
    
    for sound in [
        WT_Sound.FlapLevelAvaliable,
        WT_Sound.GearDeployable,
        WT_Sound.FlapSpeedWarning,
        WT_Sound.GearSpeedWarning,
        WT_Sound.FrameSpeedWarning,
    ]:
        sound_engine.play_sound(sound)
        y = input(f"Played {sound.name}. Press Enter to continue...")
    
    
    
    # fetcher = TelemetryFetcher("192.168.0.40")
    
    # fetcher.fetch_data()
    # telem = fetcher.get_plane_telemetry()
    # assert telem is not None, "Telemetry data should not be None"
    
    # plane = Plane(telem)
    
    # while True: 
    #     fetcher.fetch_data()
    #     new_telem = fetcher.get_plane_telemetry()
        
    #     if new_telem is None:
    #         print("No telemetry data available.")
    #         time.sleep(1)
    #         continue
        
    #     plane.update_telemetry(new_telem)
        
    #     print("Wing Sweep Lever:", plane.telemetry.wing_sweep_lever)
    #     print("Wing Sweep Indicator:", plane.telemetry.wing_sweep_indicator)
        
    #     print("Current Max Speeds:", plane.get_current_max_speeds().__dict__)
    #     print("---------------------------------")
    #     time.sleep(1)
    # pass


if __name__ == "__main__":
    main()
    # test()