import numpy as np
import wave

def generate_waveform(frequency=1000, duration=0.5, samplerate=44100, volume=0.5, waveform='sine'):
    """
    Erzeugt eine Welle der gewählten Form:
    - 'sine' : Sinus
    - 'square' : Rechteck
    - 'sawtooth' : Sägezahn
    - 'triangle' : Dreieck
    """
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)

    if waveform == 'sine':
        wave_data = np.sin(2 * np.pi * frequency * t)
    elif waveform == 'square':
        wave_data = np.sign(np.sin(2 * np.pi * frequency * t))
    elif waveform == 'sawtooth':
        wave_data = 2*(t*frequency - np.floor(0.5 + t*frequency))
    elif waveform == 'triangle':
        wave_data = 2 * np.abs(2*(t*frequency - np.floor(0.5 + t*frequency))) - 1
    else:
        raise ValueError("Wellenform muss sein: 'sine', 'square', 'sawtooth', 'triangle'")

    return volume * wave_data

def save_beep_sequence(beeps, output_file="beep_alarm.wav", samplerate=44100):
    """
    Nimmt eine Liste von (freq, duration, pause, waveform) Tupeln und erzeugt eine Sequenz.
    """
    audio = np.array([], dtype=np.float32)

    for freq, dur, pause, waveform in beeps:
        if freq > 0:
            tone = generate_waveform(frequency=freq, duration=dur, samplerate=samplerate, waveform=waveform)
            audio = np.concatenate((audio, tone))
        if pause > 0:
            silence = np.zeros(int(samplerate * pause))
            audio = np.concatenate((audio, silence))

    # Normalisieren auf 16-bit PCM
    audio = np.int16(audio / np.max(np.abs(audio)) * 32767)

    # WAV-Datei speichern
    with wave.open(output_file, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())

    print(f"✅ Beep-Alarm gespeichert: {output_file}")

if __name__ == "__main__":
    # Beispiel: Verschiedene Wellenformen
    # Format: (Frequenz [Hz], Dauer [s], Pause [s], Wellenform)
    # beep_pattern = [
    #     (1200, 0.3, 0.2, 'sine'),
    #     (1200, 0.3, 0.2, 'square'),
    #     (1000, 0.3, 0.2, 'triangle'),
    #     (800, 0.3, 0.5, 'sawtooth'),
    # ] * 2  # zweimal wiederholen
    
    beep_pattern = [
        (800, 0.1, 0.0, 'sine'),
        (1000, 0.1, 0.0, 'sine')
    ] * 1

    save_beep_sequence(beep_pattern, "info_beep.wav")
