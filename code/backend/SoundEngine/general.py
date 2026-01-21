import threading
import time
from pathlib import Path
from Packages.local_db import LocalDB


LOCAL_DB_NAME = "sound_settings"
DB = LocalDB()


class Sound(object):
    """Base class For Sounds used in the Sound Boxes.
    """
    name: str
    intervall: int | None
    identifier: str
    description: str = ""
    standard_path: str | Path
    standard_volume: float = 1.0
    priority_playback: bool = False
    
    def __init__(self, name: str, standard_path: str | Path, intervall: int | None = None, identifier: str | None = None, description: str = "", priority_playback: bool = False, volume: float = 1.0) -> None:
        self.name = name
        self.standard_path = standard_path
        self.intervall = intervall
        self.identifier = identifier if identifier is not None else name
        self.description = description
        self.priority_playback = priority_playback
        self.standard_volume = volume
        
class PlayableSound:
    """A Sound that can be played, with volume and path information. This class is not supposed to be created directly, but via SoundManager.
    """
    intervall:int|None
    volume:float
    path:str|Path
    identifier:str
    
    def __init__(self, path:str|Path, intervall:int|None, volume:float, identifier:str) -> None:
        assert volume >= 0.0 and volume <= 1.0, "Volume must be between 0.0 and 1.0"
        self.path = path
        self.intervall = intervall
        self.volume = volume
        self.identifier = identifier
    
class SoundManager:
    """Maps Sounds to Soundfiles and manages changes in those settings."""
    def __init__(self):
        data = DB.get_dict(LOCAL_DB_NAME, default={})
        self.sound_mapping = data.get("sound_mapping", {})
        self.volume_mapping = data.get("volume_mapping", {})
        # master volume as float between 0.0 and 1.0
        self.master_volume = float(data.get("master_volume", 1.0))
        
    def _save_mappings(self) -> None:
        DB.save_dict({
            "sound_mapping": self.sound_mapping,
            "volume_mapping": self.volume_mapping,
            "master_volume": self.master_volume,
        }, LOCAL_DB_NAME)
    
    def change_sound_mapping(self, sound:Sound|str, new_path:str|Path, skip_saving:bool = False) -> None:
        """Change the sound mapping for a given Sound.

        :param sound: The Sound or its identifier to change.
        :type sound: Sound | str
        :param new_path: The new path to map the sound to.
        :type new_path: str | Path
        :param skip_saving: Whether to skip saving the mappings to the database immediately.
        :type skip_saving: bool
        """
        if isinstance(sound, Sound):
            identifier = sound.identifier
        else:
            identifier = sound
        self.sound_mapping[identifier] = new_path
        if not skip_saving:
            self._save_mappings()
        
    def change_volume_mapping(self, sound:Sound|str, new_volume:float, skip_saving:bool = False) -> None:
        """Change the volume mapping for a given Sound.

        :param sound: The Sound or its identifier to change.
        :type sound: Sound | str
        :param new_volume: The new volume to map the sound to (0.0 to 1.0).
        :type new_volume: float
        :param skip_saving: Whether to skip saving the mappings to the database immediately.
        :type skip_saving: bool
        """
        if isinstance(sound, Sound):
            identifier = sound.identifier
        else:
            identifier = sound
        self.volume_mapping[identifier] = new_volume
        if not skip_saving:
            self._save_mappings()   

    def change_master_volume(self, new_volume: float, skip_saving: bool = False) -> None:
        """Change the global/master volume applied to all sounds.

        :param new_volume: new master volume between 0.0 and 1.0
        :type new_volume: float
        :param skip_saving: whether to skip saving immediately
        :type skip_saving: bool
        """
        if new_volume < 0.0:
            new_volume = 0.0
        elif new_volume > 1.0:
            new_volume = 1.0
        self.master_volume = float(new_volume)
        if not skip_saving:
            self._save_mappings()
        
    def get_playable_sound(self, sound:Sound) -> PlayableSound:
        """Get a PlayableSound for the given Sound, using user-configured settings if available.
        
        :param sound: The Sound object to get a PlayableSound for.
        :type sound: Sound
        """
        path = self.sound_mapping.get(sound.identifier, sound.standard_path)
        volume = self.volume_mapping.get(sound.identifier, sound.standard_volume)
        # apply master volume
        try:
            volume = float(volume) * float(self.master_volume)
        except Exception:
            pass
        
        obj = PlayableSound(path, sound.intervall, volume, sound.identifier)
        return obj
    
    def identifier_exists(self, identifier:str) -> bool:
        """Check if a Sound with the given identifier exists in the path mappings.
        
        :param identifier: The identifier to check.
        :type identifier: str
        :return: True if the identifier exists, False otherwise.
        :rtype: bool
        """
        saved_mapping = DB.get_dict(LOCAL_DB_NAME, default={}).get("sound_mapping", {})
        return identifier in self.sound_mapping and identifier in saved_mapping.keys()
    
class SoundQueue:
    """A circular/scheduled queue of Sound entries.
    
    Each entry stores the timestamp when it should be executed and the GeneralSound.
    pop() blocks until the next scheduled item is due and returns it. If the returned
    sound has an interval (sound.intervall), it is reinserted with its next execution
    time set to now + interval.

    The queue is thread-safe and notifies a waiting consumer when new items are added
    or removed. New sounds are scheduled for immediate execution (as soon as possible).
    """
    def __init__(self, sound_manager:SoundManager|None = None):
        """
        Initialize an empty SoundQueue.
        """
        self._items: list[dict] = []  # each item: {'time': float, 'sound': PlayableSound}
        self._cond = threading.Condition()
        self._stopped = False
        if sound_manager is not None:
            self._sound_manager = sound_manager
        else:
            self._sound_manager = SoundManager()
        
    def add_sound(self, sound:Sound, disable_periodic:bool = False) -> None:
        """Add a Sound to the queue for immediate playback.
        
        Args:
            sound (Sound): Sound object to add.
            disable_periodic (bool): If True, disable periodic playback for this sound.
        """
        playable_sound = self._sound_manager.get_playable_sound(sound)
        if disable_periodic:
            playable_sound.intervall = None
            
        with self._cond:
            self._items.append({'time': time.time(), 'sound': playable_sound})
            self._cond.notify()  # wake any waiting pop() so it can re-evaluate next item
            
    def remove_sound(self, sound:Sound | PlayableSound | str) -> None:
        """Remove all instances of the given Sound from the queue.
        
        Args:
            sound (Sound | PlayableSound | str): Sound object, PlayableSound, or identifier to remove.
        """
        if isinstance(sound, str):
            identifier = sound
        elif isinstance(sound, Sound) or isinstance(sound, PlayableSound):
            identifier = sound.identifier
        else:
            raise ValueError("sound must be a Sound, PlayableSound, or identifier string")
        
        with self._cond:
            self._items = [item for item in self._items if item['sound'].identifier != identifier]
            self._cond.notify()  # wake any waiting pop() so it can re-evaluate next item
            
    def pop(self) -> PlayableSound:
        """Pop and return the next PlayableSound that is due.

        This method blocks until an item is available and its scheduled time has arrived.
        If the returned sound has an interval (sound.intervall not None), the sound
        will be reinserted into the queue with next execution time = now + interval.

        :return: the sound ready to be played.
        :rtype: PlayableSound
        
        :raises RuntimeError: if the queue has been stopped via stop().
        """
        with self._cond:
            while True:
                if self._stopped:
                    raise RuntimeError("SoundQueue stopped")

                if not self._items:
                    # Nothing Scheduled, wait until notified
                    self._cond.wait()
                    continue
                
                # find earliest scheduled entry
                self._items.sort(key=lambda e: e['time'])
                entry = self._items[0]
                now = time.time()
                delay = entry['time'] - now
                
                if delay > 0:
                    # wait until the scheduled time or until notified (new earlier item)
                    self._cond.wait(timeout=delay)
                    continue
                
                # entry is due -> remove it
                self._items.pop(0)
                sound: PlayableSound = entry['sound']
                
                # if sound has interval, reschedule it for now + interval
                interval = getattr(sound, 'intervall', None)
                if interval is not None:
                    next_time = time.time() + interval
                    self._items.append({'time': next_time, 'sound': sound})
                    self._cond.notify()
                
                return sound
            
    def stop(self) -> None:
        """Stop the queue and wake any blocked pop() calls."""
        with self._cond:
            self._stopped = True
            self._cond.notify_all()
    
    def size(self) -> int:
        """
        Return the current number of scheduled items (approximate).
        """
        with self._cond:
            return len(self._items)
    
    def clear(self) -> None:
        """Clear the entire play loop of the queue."""
        with self._cond:
            self._items.clear()
            self._cond.notify_all()
    
    def __len__(self) -> int:
        return self.size()
    