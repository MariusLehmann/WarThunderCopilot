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