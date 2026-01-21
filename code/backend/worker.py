from PySide6.QtCore import QObject, QThread, Signal, QTimer, Slot
from Packages.Models.Plane import WTPlane
import threading
from .wtFetcher import WTUpdater, TelemetryNotFoundException, PlaneNotFoundException, TelemetryData

class AsyncPeriodicWorker(QObject):
    running_thread:QThread
    set_interval = Signal(int)
    

    def __init__(self, interval_ms:int, tread:QThread|None = None):
        """Creates a Worker which runs all <intervall_ms> ms in its own Thread

        :param interval_ms: the Intervall in ms to run the _work method of the Worker
        :type interval_ms: int
        :param tread: Thread in which the Worker runs, if None a new Thread is created, defaults to None
        :type tread: QThread | None, optional
        """
        super().__init__()
        if tread is None:
            self.running_thread = QThread()
        else:
            self.running_thread = tread
        
        self._pause_event = threading.Event()
        self.moveToThread(self.running_thread)
        
        self.timer = QTimer()
        self.timer.moveToThread(self.running_thread)
        self.timer.timeout.connect(self._call_work_function)
        self.timer.setInterval(interval_ms)
        # Connect signal for thread-safe interval updates
        self.set_interval.connect(self._on_set_interval)
        self.running_thread.started.connect(self._on_thread_started)
        self.running_thread.finished.connect(self._on_thread_finished)
        self.running_thread.start()

    @Slot()
    def _on_thread_started(self) -> None:
        # Ensure `timer.start()` runs in the thread that owns the QTimer
        self.timer.start()

    @Slot()
    def _on_thread_finished(self) -> None:
        # Ensure `timer.stop()` runs in the thread that owns the QTimer
        self.timer.stop()

    @Slot(int)
    def _on_set_interval(self, interval_ms: int) -> None:
        # This slot is executed in the worker's thread; safe to call QTimer.setInterval
        self.timer.setInterval(interval_ms)
        
    def _call_work_function(self):
        if not self._pause_event.is_set():
            self._work()
            
    def _work(self):
        # Has to be implemented by child Classes
        raise NotImplementedError
    
    def update_intervall(self, interval_ms:int):
        """Update the intervall i which the Worker runs

        :param interval_ms: the new Intervall in ms
        :type interval_ms: int
        """
        # Emit a signal so the actual setInterval runs in the QTimer's thread
        self.set_interval.emit(interval_ms)
    
    def stop(self):
        """Stop the Worker and its Thread
        """
        self.running_thread.quit()
    
    def pause(self):
        """Pause the Worker (stops the timer)
        """
        self._pause_event.set()
    
    def resume(self):
        """Resume the Worker (starts the timer)
        """
        self._pause_event.clear()
        
class dataFetcher(AsyncPeriodicWorker):
    # Signals Emitted by this Worker
    new_plane_data = Signal(WTPlane)
    new_telemetry_data = Signal(TelemetryData)
    new_map_data = Signal(dict) #TODO: Implement with Map Support

    
    def __init__(self,endpoint_ip:str, debug_mode:bool = False, std_intervall_ms:int = 100, error_intervall_ms:int = 5000):
        """Create a Worker to fetch data from the local WT-Web-Endpoint

        :param endpoint_ip: The Address of the local Warthunder web endpoint
        :type endpoint_ip: str
        :param debug_mode: If True, data is fetched from a local File instad of the Web Endpoint, defaults to False
        :type debug_mode: bool, optional
        :param std_intervall_ms: The intervall of running this Worker in ms as long as no errors occured, defaults to 100
        :type std_intervall_ms: int, optional
        :param error_intervall_ms: The intervall of running this Worker in ms as long as an error occured, defaults to 5000
        :type error_intervall_ms: int, optional
        
        Signals:
            new_plane_data (WTPlane): Emitted when planer type was changed ingame, sends new Plane Data (e.g., plane type changes).
            new_telemetry_data (dict): Emitted when new telemetry data is fetched.
            new_map_data (dict): Emitted when new map data is available (TODO: Implement with Map Support).
        """
        super().__init__(std_intervall_ms)
        self.running_thread.setObjectName("dataFetcherThread")
        self.std_intervall = std_intervall_ms
        self.error_intervall = error_intervall_ms
        self.fetcher = WTUpdater(endpoint_ip, debug_mode)
        self.own_plane: WTPlane|None = None
        self.__last_was_success = True
        self.__debug_mode = debug_mode
    
    def on_ip_change(self, new_ip:str):
        """Update the Endpoint IP of the fetcher

        :param new_ip: The new IP Address of the local Warthunder web endpoint
        :type new_ip: str
        """
        self.fetcher = WTUpdater(new_ip, self.__debug_mode)
    
    def _work(self):
        errors_occured = False
        error = None
        tel = None
        try:
            self.fetcher.fetch_data()
            tel = self.fetcher.get_plane_telemetry()
        except (TelemetryNotFoundException, PlaneNotFoundException) as e:
            print(e)
            errors_occured = True
            error = e
        
        if not errors_occured and tel is not None:
            self.new_telemetry_data.emit(tel)
            
            if self.own_plane is None or not (self.own_plane.planetype == tel.planetype): 
                self.own_plane = WTPlane(tel.planetype)
                self.new_plane_data.emit(self.own_plane)
            
            self.own_plane.set_telemetry(tel)
            self.__on_success()
        else:
            if errors_occured and error is not None: 
                self.__on_error(error)
            elif tel is None:
                self.__on_error(TelemetryNotFoundException("No Telemetry found while Update run."))
            else:
                self.__on_error(RuntimeError("Unknown error occured"))
                
                
    def __on_error(self, error:Exception) -> None:
        """set update rate to self.error_intervall
        """
        if self.__last_was_success:
            self.__last_was_success = False
            self.update_intervall(self.error_intervall)
        
    
    def __on_success(self) -> None:
        """set update rate to self.std_intervall
        """
        if not self.__last_was_success:
            self.__last_was_success = True
            self.update_intervall(self.std_intervall)
            