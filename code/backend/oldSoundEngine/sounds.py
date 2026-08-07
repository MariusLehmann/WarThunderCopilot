from .general import Sound
from paths import SOUNDS_DIR

class FlapInfoSound(Sound):
    def __init__(self) -> None:
        super().__init__(
            name = "flap_info",
            standard_path = SOUNDS_DIR / "flap_info.wav",
            intervall= None,
            identifier= "flap_available_info",
            description= "info sound for flap deployment availability",
            priority_playback= True
        )

class SpeedWarningSound(Sound):
    def __init__(self) -> None:
        super().__init__(
            name = "speed_warning",
            standard_path = SOUNDS_DIR / "speed_warning.wav",
            intervall= 1,
            identifier= "speed_warning",
            description= "speed too high for the airframe"
        )

class FlapSpeedWarningSound(Sound):
    def __init__(self) -> None:
        super().__init__(
            name = "flap_speed_warning",
            standard_path = SOUNDS_DIR / "flap_speed_warning.wav",
            intervall= 1,
            identifier= "flap_speed_warning",
            description= "speed too high for current flap setting"
        )

class GearSpeedWarningSound(Sound):
    def __init__(self) -> None:
        super().__init__(
            name = "gear_speed_warning",
            standard_path = SOUNDS_DIR / "retract_gear.wav",
            intervall= 1,
            identifier= "gear_speed_warning",
            description= "speed too high for gear deployed"
        )