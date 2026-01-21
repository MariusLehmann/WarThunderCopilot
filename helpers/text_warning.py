import pyttsx3
from pydub import AudioSegment, effects
import os

def create_speed_warning_wav(output_file, text):
    engine = pyttsx3.init()

    # Stimme auswählen (weiblich, falls vorhanden)
    voices = engine.getProperty('voices')
    for v in voices:
        if "female" in v.name.lower() or "frau" in v.name.lower() or "zira" in v.name.lower():
            engine.setProperty('voice', v.id)
            break

    engine.setProperty('rate', 160)   # langsamer -> Warnsystem-artig
    engine.setProperty('volume', 1.0) # maximale Lautstärke

    # Temporäre Datei zur Sprachausgabe
    temp_file = "temp_voice.wav"
    engine.save_to_file(text, temp_file)
    engine.runAndWait()

    # Mit pydub öffnen und Effekte anwenden
    sound = AudioSegment.from_wav(temp_file)

    # Normalisieren + Bandpass (Telefon-/Cockpit-Sound)
    sound = effects.normalize(sound)
    sound = sound.low_pass_filter(3000).high_pass_filter(400)

    # Leichte Verzerrung / Robotisierung
    sound = sound + 6  # lauter machen
    # Vermeide Phasenauslöschung: statt einer invertierten Kopie (die auf einem Kanal
    # zu Stille oder Störgeräuschen führen kann) verwenden wir eine leicht verzögerte,
    # leisere und nach links gepannte Kopie. Das erzeugt einen "metallischen"/chorusartigen
    # Effekt ohne destruktive Interferenz zwischen linken und rechten Kanal.
    delay_ms = 20
    copy = (AudioSegment.silent(duration=delay_ms) + sound) - 8  # verzögert und -8 dB
    copy = copy.pan(-0.5)
    sound = sound.overlay(copy)

    # Export als fertige Datei
    sound.export(output_file, format="wav")
    os.remove(temp_file)

    print(f"✅ Speed Warning WAV-Datei erstellt: {output_file}")

if __name__ == "__main__":
    create_speed_warning_wav("retract_gear.wav","retract Gear!")

