import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

import pygame
from PySide6.QtCore import QObject, Signal, Slot

from logging_setup import get_logger
from paths import SOUNDS_DIR, USER_SOUNDS_DIR
from .settings import SoundSettings, SoundProperties

from Packages.local_db import LocalDB
DB = LocalDB()

logger = get_logger(__name__, filename='SoundEngine.log')


def get_default_sound_properties(identifier: str) -> SoundProperties:
    """Returns default SoundProperties for a given sound identifier."""
    default_properties = {
        "flap_level_available": SoundProperties("flap_level_available", str(SOUNDS_DIR / "flap_info.wav")),
        "gear_deployable": SoundProperties("gear_deployable", str(SOUNDS_DIR / "gear_info.wav")),
        "flap_speed_warning": SoundProperties("flap_speed_warning", str(SOUNDS_DIR / "flap_speed_warning.wav")),
        "gear_speed_warning": SoundProperties("gear_speed_warning", str(SOUNDS_DIR / "retract_gear.wav")),
        "frame_speed_warning": SoundProperties("frame_speed_warning", str(SOUNDS_DIR / "speed_warning.wav")),
    }
    return default_properties[identifier]


@dataclass
class Sound:
    identifier: str
    name: str
    description: str

class WT_Sound(Enum):
    FlapLevelAvaliable = Sound(identifier="flap_level_available", name="Flap Level Available", description="Sound for when flaps can be deployed safely.")
    GearDeployable = Sound(identifier="gear_deployable", name="Gear Deployable", description="Sound for when gear can be deployed safely.")
    FlapSpeedWarning = Sound(identifier="flap_speed_warning", name="Flap Speed Warning", description="Sound for when plane speed reaches the limit for the current flap level.")
    GearSpeedWarning = Sound(identifier="gear_speed_warning", name="Gear Speed Warning", description="Sound for when plane speed reaches the limit for the deployed gear.")
    FrameSpeedWarning = Sound(identifier="frame_speed_warning", name="Frame Speed Warning", description="Sound for when plane speed reaches the limit for the frame.")


class _SoundPlayer:
    """Runs a single dedicated worker thread that plays sounds from a FIFO queue.

    A `serial` player (used for the regular queues) plays one sound at a
    time, waiting for it to finish before starting the next - this keeps
    playback order stable and predictable. A non-serial player (used for
    immediate/overlapping playback) fires each sound off on its own pygame
    channel without waiting for it to finish, so several sounds can
    genuinely play on top of each other.
    """

    def __init__(self, name: str, serial: bool = True) -> None:
        self._name = name
        self._serial = serial

        self._items: list[tuple[str, SoundProperties]] = []
        self._currently_playing: str | None = None
        self._cond = threading.Condition()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")

        self._thread = threading.Thread(target=self._run, name=f"SoundPlayer-{name}", daemon=True)
        self._thread.start()

    def enqueue(self, identifier: str, properties: SoundProperties) -> None:
        """Schedule a sound for playback on this player."""
        with self._cond:
            self._items.append((identifier, properties))
            self._cond.notify()

    def remove(self, identifiers: set[str]) -> int:
        """Remove all not-yet-played entries whose identifier is in `identifiers`.

        Sounds that are already playing are not affected.

        :return: number of removed entries.
        """
        with self._cond:
            before = len(self._items)
            self._items = [item for item in self._items if item[0] not in identifiers]
            self._cond.notify()
            return before - len(self._items)

    def contains(self, identifier: str) -> bool:
        """Whether `identifier` is currently queued or playing on this player."""
        with self._cond:
            if identifier == self._currently_playing:
                return True
            return any(item[0] == identifier for item in self._items)

    def clear(self) -> None:
        """Remove all not-yet-played entries from this player's queue."""
        with self._cond:
            self._items.clear()
            self._cond.notify()

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()
        with self._cond:
            self._cond.notify()

    def stop(self, wait: bool = False) -> None:
        with self._cond:
            self._stop_event.set()
            self._cond.notify_all()
        if wait:
            self._thread.join(timeout=5.0)

    def _run(self) -> None:
        """Worker loop: waits for queued sounds and plays them one by one."""
        while not self._stop_event.is_set():
            with self._cond:
                while not self._items and not self._stop_event.is_set():
                    self._cond.wait()
                if self._stop_event.is_set():
                    return
                if self._pause_event.is_set():
                    self._cond.wait(timeout=0.2)
                    continue

                identifier, properties = self._items.pop(0)
                self._currently_playing = identifier

            try:
                self._play(properties)
            except Exception as e:
                logger.error(f"SoundPlayer '{self._name}' failed to play sound '{identifier}': {e}")
            finally:
                self._currently_playing = None

    def _play(self, properties: SoundProperties) -> None:
        """Play a single sound. Blocks until finished if this player is `serial`."""
        snd = pygame.mixer.Sound(str(properties.file_path))
        snd.set_volume(max(0.0, min(1.0, properties.volume)))

        channel = pygame.mixer.find_channel(force=True)
        if channel is None:
            # No channel could be allocated at all - fall back to fire-and-forget.
            snd.play()
            time.sleep(snd.get_length())
            return

        channel.play(snd)
        if self._serial:
            while channel.get_busy() and not self._stop_event.is_set():
                time.sleep(0.01)


class SoundEngine(QObject):
    """Central engine for scheduling and playing notification sounds.

    Regular sounds are appended to a queue and played one after another by
    a dedicated worker thread. Sounds whose `SoundProperties.overlapping` is
    set (or that are explicitly requested with `immediate=True`) skip the
    queue and are played right away on a separate worker, so they can sound
    in parallel with whatever else is currently playing.

    Additional named queues - each with their own dedicated worker/player -
    can be created via `create_queue()` and targeted from `play_sound()`.
    """

    DEFAULT_QUEUE = "default"
    _IMMEDIATE_QUEUE = "__immediate__"

    def __init__(self):
        super().__init__()
        self._sound_settings = SoundSettings.load_from_db()

        self._players_lock = threading.Lock()
        self._players: dict[str, _SoundPlayer] = {
            self.DEFAULT_QUEUE: _SoundPlayer(self.DEFAULT_QUEUE, serial=True),
            self._IMMEDIATE_QUEUE: _SoundPlayer(self._IMMEDIATE_QUEUE, serial=False),
        }

    def create_queue(self, name: str) -> None:
        """Create an additional named queue with its own dedicated player/thread.

        :param name: Unique name for the new queue.
        :type name: str
        :raises ValueError: if `name` is reserved or already in use.
        """
        if name == self._IMMEDIATE_QUEUE:
            raise ValueError(f"Queue name '{name}' is reserved.")

        with self._players_lock:
            if name in self._players:
                raise ValueError(f"Queue '{name}' already exists.")
            self._players[name] = _SoundPlayer(name, serial=True)

    def play_sound(self, sound: WT_Sound, immediate: bool = False, queue: str = DEFAULT_QUEUE) -> None:
        """Schedule a sound for playback.

        The sound's properties are looked up in the current SoundSettings
        (falling back to built-in defaults). If `immediate` is True or the
        sound's properties have `overlapping` set, the sound is played right
        away, in parallel to anything else currently playing. Otherwise it
        is appended to `queue`.

        :param sound: The sound to play.
        :type sound: WT_Sound
        :param immediate: Play the sound right away instead of queueing it.
        :type immediate: bool
        :param queue: Name of the queue to play the sound in, if not immediate.
            Must have been created via `create_queue()`, or be the default queue.
        :type queue: str
        :raises ValueError: if `queue` does not refer to a known queue.
        """
        properties = self.__get_properties(sound)
        # Master-Volume erst hier auf eine Kopie anwenden (statt die gespeicherten
        # properties zu mutieren) - sonst würde sich der Faktor bei jedem Abspielen
        # erneut mit der zuvor schon reduzierten Lautstärke multiplizieren.
        effective_properties = SoundProperties(
            name=properties.name,
            file_path=properties.file_path,
            volume=properties.volume * self._sound_settings.master_volume,
            overlapping=properties.overlapping,
        )

        if immediate or properties.overlapping:
            self._players[self._IMMEDIATE_QUEUE].enqueue(sound.value.identifier, effective_properties)
            return

        player = self._players.get(queue)
        if player is None:
            raise ValueError(f"Unknown queue '{queue}'. Create it first via create_queue().")
        player.enqueue(sound.value.identifier, effective_properties)

    def stop_sound(self, sound: WT_Sound | Iterable[WT_Sound], queue: str | None = None) -> int:
        """Remove not-yet-played occurrences of the given sound(s) from the queue(s).

        Counterpart to `play_sound`. Sounds that are already playing are not
        interrupted - only entries still waiting in a queue are removed.

        :param sound: A single sound, or an iterable of sounds, to remove.
        :type sound: WT_Sound | Iterable[WT_Sound]
        :param queue: If given, only remove from this queue. Otherwise all
            regular queues are searched (the immediate player is never queued).
        :type queue: str | None
        :return: Number of removed entries.
        :rtype: int
        """
        sounds = [sound] if isinstance(sound, WT_Sound) else list(sound)
        identifiers = {s.value.identifier for s in sounds}

        with self._players_lock:
            if queue is not None:
                player = self._players.get(queue)
                if player is None:
                    raise ValueError(f"Unknown queue '{queue}'.")
                targets = [player]
            else:
                targets = [p for name, p in self._players.items() if name != self._IMMEDIATE_QUEUE]

        return sum(player.remove(identifiers) for player in targets)

    def __get_properties(self, sound: WT_Sound) -> SoundProperties:
        identifier = sound.value.identifier
        properties = self._sound_settings.sounds.get(identifier)
        if not properties:
            properties = get_default_sound_properties(identifier)
            self._sound_settings.sounds[identifier] = properties
        return properties

    @Slot(list)
    def on_new_information_sounds(self, sounds: list[WT_Sound]):
        """Play every given sound that is not already queued or playing.

        :param sounds: Sounds reported by the information/warning engine.
        :type sounds: list[WT_Sound]
        """
        for sound in sounds:
            identifier = sound.value.identifier
            with self._players_lock:
                players = list(self._players.values())
            if any(player.contains(identifier) for player in players):
                continue
            self.play_sound(sound)

    @Slot(SoundSettings)
    def on_new_sound_settings(self, sound_settings: SoundSettings):
        self._sound_settings = sound_settings

    def stop(self, wait: bool = False) -> None:
        """Stop all players and their worker threads."""
        with self._players_lock:
            players = list(self._players.values())
        for player in players:
            player.stop(wait=wait)

    def pause(self) -> None:
        """Pause playback on all players."""
        with self._players_lock:
            players = list(self._players.values())
        for player in players:
            player.pause()

    def resume(self) -> None:
        """Resume playback on all players."""
        with self._players_lock:
            players = list(self._players.values())
        for player in players:
            player.resume()
