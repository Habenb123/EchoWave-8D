import numpy as np


import numpy as np

def moving_pan(audio, sr, speed=0.08, phase=0):

    t = np.arange(len(audio)) / sr

    pan = np.sin(
        2*np.pi*speed*t + phase
    )

    left = np.sqrt((1-pan)/2)
    right = np.sqrt((1+pan)/2)

    output = np.zeros_like(audio)

    output[:,0] = audio[:,0] * left
    output[:,1] = audio[:,1] * right

    return output

def interaural_delay(audio, sr, max_delay_ms=2):
    """
    Small ear delay to improve immersion.
    """

    delay = int(sr * max_delay_ms / 1000)

    output = np.copy(audio)

    output[delay:, 1] = audio[:-delay, 1]

    return output