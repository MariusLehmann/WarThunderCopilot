from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon



from gui.settings_window import SettingsDialog
from gui.main_window import MainWindow


import time


        
            
def main():
    app = QApplication([])
    app.setWindowIcon(QIcon("icon.ico"))

    dialog = SettingsDialog()
    if dialog.exec():
        settings = dialog.get_settings()
        # Theme direkt setzen
        settings.apply_theme()
        
        window = MainWindow(settings)
        window.show()
        app.exec()

def test():
    # i = 0 
    # warn = FlapSpeedWarning()
    
    # while i < 10:
    #     i += 1
    #     warn.play_sound()
    #     time.sleep(warn.intervall/1000)
    
    
    

    # plane = WTPlane("am-1")
    # updater = WTUpdater("192.168.0.40")
    # updater.fetch_data()
    # print(plane.telemetry)
    # print(updater.get_plane_telemetry())
    pass


if __name__ == "__main__":
    main()
    # test()