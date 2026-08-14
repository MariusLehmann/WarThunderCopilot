"""MainWorker: zentraler Hintergrund-Thread für alles, was mit dem Beschaffen und
Verarbeiten neuer Spiel-/API-Daten zu tun hat (Telemetrie-Fetch + Plane-Anreicherung).

Läuft in einem eigenen QThread neben dem GUI-Thread, wird einmalig erzeugt/gestartet
und arbeitet danach periodisch mit einer zur Laufzeit einstellbaren Frequenz.

Bewusst eigenständig gehalten: importiert nur Packages/backend-Bausteine, die
schon vorher isoliert waren (TelemetryFetcher, Plane). Es gibt noch KEINE
Verbindung zu MainWindow, SettingsWindow oder PlaneSpeedWarningEngine - die
Integrationspunkte sind unten als TODOs markiert und füllen wir als nächstes
gemeinsam.
"""
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
import threading

from Models import Plane, PlaneFetchError
from backend.telemetry_fetcher import TelemetryFetcher, TelemetryNotFoundException, PlaneNotFoundException


class MainWorker(QObject):
    """Periodischer Hintergrund-Worker: holt Telemetrie + Plane-Stammdaten und
    meldet Ergebnisse ausschließlich über Signale zurück (kein direkter
    Methodenaufruf von außen während des laufenden Betriebs).

    Signale:
        S_NewPlane(Plane): Neues Flugzeug erkannt (Typwechsel gegenüber dem
            zuletzt bekannten Flugzeug). Das Plane-Objekt trägt bereits die
            aktuelle Telemetrie.
        S_NoPlane(): Aktuell ist kein Flugzeug/keine Telemetrie verfügbar
            (z.B. Hangar, Menü, Spiel nicht erreichbar).
        S_TelUpdate(Plane): Das bisher bekannte Flugzeug hat neue Telemetrie
            erhalten (kein Typwechsel).
    """

    S_NewPlane = Signal(Plane)
    S_NoPlane = Signal(str)  # Signal with error message
    S_TelUpdate = Signal(Plane)

    # Intern für thread-sicheren Intervall-Wechsel, siehe set_interval().
    _interval_changed = Signal(int)

    # Anzahl aufeinanderfolgender Fehl-Fetches, die stillschweigend toleriert werden
    # (kein Signal, kein Backoff), bevor S_NoPlane emittiert wird. Überspielt kurze,
    # vereinzelte Aussetzer, ohne dass andere Module davon überhaupt etwas mitbekommen.
    RUNS_BEFORE_NO_PLANE = 5

    def __init__(
        self,
        endpoint_ip: str,
        api_url: str,
        interval_ms: int = 100,
        debug_mode: bool = False,
        max_error_interval_ms: int = 10_000,
        error_backoff_factor: float = 1.5,
        runs_before_no_plane: int = RUNS_BEFORE_NO_PLANE,
    ):
        """
        :param endpoint_ip: IP des lokalen War-Thunder-API-Endpunkts.
        :param api_url: URL des Backend-API-Endpunkts.
        :param interval_ms: Basis-Abfrageintervall in ms, solange keine Fehler
            auftreten. Soll später aus GeneralSettings.intervall kommen (siehe
            TODO unten).
        :param debug_mode: Wenn True, werden Debug-Daten (debug-data.json)
            statt der echten lokalen WT-API genutzt.
        :param max_error_interval_ms: Obergrenze für das Intervall, auf die bei
            anhaltenden Fehlern maximal hochgefahren wird (Ressourcenschonung).
        :param error_backoff_factor: Faktor, um den das Intervall pro weiterem
            Fehler-Tick wächst, sobald die Gnadenfrist überschritten ist.
        :param runs_before_no_plane: Anzahl aufeinanderfolgender Fehl-Fetches,
            die noch stillschweigend (ohne Signal, ohne Backoff) toleriert
            werden, siehe RUNS_BEFORE_NO_PLANE.
        """
        super().__init__()

        self._fetcher = TelemetryFetcher(endpoint_ip, debug_mode)
        self._api_url = api_url
        self._current_plane: Plane | None = None

        self._base_interval_ms = interval_ms
        self._max_error_interval_ms = max_error_interval_ms
        self._error_backoff_factor = error_backoff_factor
        self._runs_before_no_plane = runs_before_no_plane
        self._consecutive_errors = 0

        # -- Thread-Infrastruktur --
        self._thread = QThread()
        self._thread.setObjectName("MainWorkerThread")
        self.moveToThread(self._thread)

        self._timer = QTimer()
        self._timer.moveToThread(self._thread)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._run_once)

        self._pause_event = threading.Event()

        self._thread.started.connect(self._timer.start)
        self._thread.finished.connect(self._timer.stop)
        self._interval_changed.connect(self._on_interval_changed)

    # ---- Lifecycle ----

    def start(self) -> None:
        """Startet den Worker-Thread. Soll einmalig beim App-Start aufgerufen werden.
        """
        self._thread.start()

    def stop(self) -> None:
        """Stoppt den Worker-Thread sauber (blockierend, bis der Thread beendet ist)."""
        self._thread.quit()
        self._thread.wait()

    def pause(self) -> None:
        """Pausiert die periodische Arbeit (Thread bleibt am Leben, Timer-Ticks werden übersprungen)."""
        self._pause_event.set()

    def resume(self) -> None:
        """Setzt eine pausierte Worker-Instanz fort."""
        self._pause_event.clear()

    # ---- Laufzeit-Konfiguration ----

    def set_interval(self, interval_ms: int) -> None:
        """Ändert die Abfragefrequenz zur Laufzeit, thread-sicher.
        """
        self._interval_changed.emit(interval_ms)

    @Slot(int)
    def _on_interval_changed(self, interval_ms: int) -> None:
        # Läuft dank moveToThread garantiert im Worker-Thread -> QTimer.setInterval ist hier sicher.
        # Eine explizite Settings-Änderung setzt auch das Basisintervall neu, auf das nach
        # Fehlern/Backoff bzw. bei Erfolg wieder zurückgesprungen wird.
        self._base_interval_ms = interval_ms
        self._timer.setInterval(interval_ms)

    def set_endpoint_ip(self, ip: str) -> None:
        """Ändert die Ziel-IP des War-Thunder-Endpunkts zur Laufzeit.
        """
        self._fetcher.set_ip_addr(ip)

    def set_api_url(self, url: str) -> None:
        """Ändert die Ziel-URL des War-Thunder-Endpunkts zur Laufzeit (nur für Debug-Modus)."""
        self._api_url = url

    # ---- Fehler-Backoff ----
    # Läuft ausschließlich innerhalb von _run_once, also schon im Worker-Thread ->
    # kein Umweg über ein Signal wie bei set_interval() nötig.

    def _apply_error_backoff(self) -> None:
        """Erhöht den Poll-Takt nach wiederholten Fehlern in Folge, um Ressourcen zu sparen.

        Wird erst aufgerufen, nachdem die Gnadenfrist (RUNS_BEFORE_NO_PLANE) bereits
        überschritten ist (siehe _run_once). Das Intervall wächst multiplikativ mit
        `_error_backoff_factor`, gedeckelt durch `_max_error_interval_ms`.
        """
        current = self._timer.interval()
        new_interval = min(int(current * self._error_backoff_factor), self._max_error_interval_ms)
        if new_interval > current:
            self._timer.setInterval(new_interval)

    def _reset_error_backoff(self) -> None:
        """Setzt den Fehler-Backoff zurück und stellt sofort wieder den Basistakt her,
        damit nach einem erfolgreichen Fetch möglichst schnell wieder normal reagiert wird.
        """
        self._consecutive_errors = 0
        if self._timer.interval() != self._base_interval_ms:
            self._timer.setInterval(self._base_interval_ms)

    # ---- Periodische Arbeit ----

    @Slot()
    def _run_once(self) -> None:
        """Wird periodisch vom internen QTimer aufgerufen (läuft im Worker-Thread).

        Holt neue Telemetrie, entscheidet ob sich das Flugzeug geändert hat
        oder ganz verschwunden ist, und emittiert das passende Signal.
        """
        if self._pause_event.is_set():
            return

        try:
            self._fetcher.fetch_data()
            telemetry = self._fetcher.get_plane_telemetry()
        except (TelemetryNotFoundException, PlaneNotFoundException)as e:
            telemetry = None

        if telemetry is None:
            self._consecutive_errors += 1
            if self._consecutive_errors < self._runs_before_no_plane:
                # Innerhalb der Gnadenfrist: vereinzelte/kurzfristige Fetch-Fehler
                # stillschweigend überspielen -- kein Signal, kein Backoff, einfach
                # beim nächsten Tick erneut versuchen.
                return

            # Gnadenfrist überschritten: Zustand verwerfen, damit kein inkonsistenter
            # alter Stand angezeigt wird. Alle abonnierten Module sollen sich auf
            # S_NoPlane deaktivieren/ausblenden und erst auf das nächste S_NewPlane
            # wieder reagieren.
            self._current_plane = None
            self._apply_error_backoff()
            self.S_NoPlane.emit("No telemetry data available.")
            return

        self._reset_error_backoff()

        if self._current_plane is None or self._current_plane.planetype != telemetry.planetype:
            try:
                self._current_plane = Plane(telemetry)
            except PlaneFetchError as e:
                self.S_NoPlane.emit(str(e))
                return
            self.S_NewPlane.emit(self._current_plane)
        else:
            self._current_plane.update_telemetry(telemetry)
            self.S_TelUpdate.emit(self._current_plane)


# ---- TODO Integration (nächster gemeinsamer Schritt) ----
# - MainWindow: eine MainWorker-Instanz statt PlaneUpdateWorker erzeugen und
#   worker.start() beim Start aufrufen.
# - S_NewPlane / S_TelUpdate: an alles anbinden, was bisher new_plane_data /
#   new_telemetry_data von PlaneUpdateWorker gehört hat. Achtung: die
#   PlaneSpeedWarningEngine erwartet aktuell in on_new_telemetry ein
#   TelemetryData-Objekt, kein Plane -- Signatur dort ggf. anpassen
#   (plane.telemetry liegt ja schon vor).
# - S_NoPlane: neuer Signalpfad ohne Entsprechung im alten Code -- z.B. um GUI-
#   Anzeigen ("Kein Flugzeug erkannt") zurückzusetzen. Dafür existiert aktuell
#   noch kein Handler.
# - set_interval() / set_endpoint_ip(): an SettingsWindow.general_settings_changed
#   anbinden (ersetzt MainWindow._on_general_settings_change's fetcher_worker-Neustart).
# - Nach erfolgreicher Anbindung: backend/worker.py (AsyncPeriodicWorker,
#   PlaneUpdateWorker) entfernen, MainWorker übernimmt deren Rolle vollständig.
