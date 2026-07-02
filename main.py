import librosa
import soundfile as sf
import numpy as np

from pedalboard import Pedalboard, Reverb

from effects import moving_pan, interaural_delay

# Load stems
vocals, sr = librosa.load(
    "separated/htdemucs/song/vocals.wav",
    sr=None,
    mono=False
)

drums, _ = librosa.load(
    "separated/htdemucs/song/drums.wav",
    sr=None,
    mono=False
)

bass, _ = librosa.load(
    "separated/htdemucs/song/bass.wav",
    sr=None,
    mono=False
)

other, _ = librosa.load(
    "separated/htdemucs/song/other.wav",
    sr=None,
    mono=False
)

# Convert to (samples, channels)
vocals = vocals.T
drums = drums.T
bass = bass.T
other = other.T

# Convert mono to stereo if necessary
def stereo(audio):
    if audio.ndim == 1:
        return np.stack([audio, audio], axis=1)
    return audio

vocals = stereo(vocals)
drums = stereo(drums)
bass = stereo(bass)
other = stereo(other)

vocals = moving_pan(
    vocals,
    sr,
    speed=0.03,
    phase=0
)

drums = moving_pan(
    drums,
    sr,
    speed=0.11,
    phase=np.pi/2
)

bass = moving_pan(
    bass,
    sr,
    speed=0.05,
    phase=np.pi
)

other = moving_pan(
    other,
    sr,
    speed=0.08,
    phase=3*np.pi/2
)

vocals = interaural_delay(vocals, sr)

drums = interaural_delay(drums, sr)

bass = interaural_delay(bass, sr)

other = interaural_delay(other, sr)

mix = vocals + drums + bass + other

board = Pedalboard([
    Reverb(room_size=0.35)
])

mix = board(mix, sr)

mix /= np.max(np.abs(mix))

sf.write(
    "output/final_8d.wav",
    mix,
    sr
)
