import pygame
import threading
from logging_setup import get_logger
import time
from PySide6.QtCore import QObject, QThread, Signal

from .general import Sound, PlayableSound, SoundManager, SoundQueue

# module logger (creates a per-module log file in `code/logs/soundBox.log`)
logger = get_logger(__name__, filename='soundBox.log')

class SoundBox:
    """A SoundBox manages the playback of sounds in its own thread.
        It uses a SoundQueue to schedule sounds for playback.
        Sounds can be added or removed from the box, and it will handle
        playing them on a dedicated pygame mixer channel.
    """
    def __init__(self, channel_index: int = 0, sound_manager:SoundManager|None = None) -> None:
        """
        Create a SoundBox and start the internal worker thread.

        Args:
            channel_index (int): pygame Channel index used by this box for playback.
        """

        # initialize pygame mixer if not already initialized
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            # If pygame is unavailable or init fails, the box will remain idle.
            pass

        self._channel_index = channel_index
        self._queue = SoundQueue(sound_manager=sound_manager)
        
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        # start worker thread
        self._thread = threading.Thread(
            target=self._internal_worker_loop, 
            name=f"SoundBoxWorker-{channel_index}", 
            daemon=True
        )
        self._thread.start()
        
    def add_sound(self, sound: Sound, disable_periodic:bool = False) -> None:
        """Add a sound to the box's play loop.

        :param sound: Sound object to schedule.
        :type sound: Sound
        :param disable_periodic: If True, disable periodic playback for this sound.
        :type disable_periodic: bool
        
        :raises AssertionError: If sound is not of type Sound.
        """
        assert isinstance(sound, Sound)
        self._queue.add_sound(sound, disable_periodic=disable_periodic)
    
    def remove_sound(self, sound: Sound) -> None:
        """Remove all occurrences of a sound from the play loop.

        :param sound: Sound object to remove.
        :type sound: Sound 
        
        :raises AssertionError: If sound is not of type Sound.
        """
        assert isinstance(sound, Sound)
        # Remove from queue
        self._queue.remove_sound(sound)
    
    def clear_queue(self) -> None:
        """Clear all sounds from the play loop."""
        self._queue.clear()
        
    def stop(self, wait: bool = False) -> None:
        """Stop the SoundBox and its internal thread.
        
        :param wait: If True, wait for the thread to finish.
        :type wait: bool
        """
        self._stop_event.set()
        self._queue.stop()
        if wait:
            self._thread.join(timeout=5.0)
            
    def pause(self) -> None:
        """Pause the SoundBox (stops playback)."""
        self._pause_event.set()
        
    def resume(self) -> None:
        """Resume the SoundBox (resumes playback)."""
        self._pause_event.clear()
        
        
    def _internal_worker_loop(self):
        """Internal worker loop that waits for scheduled sounds and plays them.
        This loop runs in a background thread.
        """
        channel = None
        try:
            channel = pygame.mixer.Channel(self._channel_index)
        except Exception:
            # pygame not available -> thread remains idle
            channel = None
            
        while not self._stop_event.is_set():
            if not self._pause_event.is_set():
                try:
                    sound = self._queue.pop()
                except RuntimeError:
                    # Queue has been stopped
                    break
                except Exception as e:
                    logger.error(f"SoundBox Worker encountered an error while popping sound: {e}")
                    time.sleep(0.1)
                    continue
                
                # Play Sound
                try:
                    snd = pygame.mixer.Sound(str(sound.path))
                    # Respect optional per-sound volume (0.0 .. 1.0) if provided
                    try:
                        vol = getattr(sound, 'volume', None)
                        if vol is not None:
                            vol = float(vol)
                            if vol < 0.0:
                                vol = 0.0
                            elif vol > 1.0:
                                vol = 1.0
                            snd.set_volume(vol)
                    except Exception:
                        # If anything goes wrong reading/setting volume, ignore and continue
                        pass
                    if channel is None:
                        try:
                            ch = pygame.mixer.find_channel()
                        except Exception:
                            ch = None
                    else:
                        ch = channel
                    
                    if ch is not None:
                        ch.play(snd)
                        while ch.get_busy() and not self._stop_event.is_set():
                            time.sleep(0.01)
                    else:
                        snd.play()
                        time.sleep(snd.get_length())
                
                except Exception as e:
                    logger.error(f"SoundBox Worker encountered an error while playing sound: {e}")
            else:
                time.sleep(0.1)
                