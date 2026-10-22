import math
import random
from array import array

import pygame

# Music and sound effects are synthesised in code, so the game needs no audio files.
# Low sample rate and square/triangle waves keep it in the chunky chiptune style of the pixel art.
RATE = 11025
MUSIC_VOLUME = 0.22
SFX_VOLUME = 0.5

# Each track is a list of layers. A layer is a list of (midi note or None for a rest, beats, wave, volume, decay).
# Every layer in a track adds up to 16 beats, so the loop lines up.
TRACKS = {
    "menu": {
        "bpm": 84,
        "layers": [
            [(72, 1, "triangle", 0.5, 2.5), (76, 1, "triangle", 0.5, 2.5), (79, 1, "triangle", 0.5, 2.5), (76, 1, "triangle", 0.5, 2.5),
             (74, 1, "triangle", 0.5, 2.5), (77, 1, "triangle", 0.5, 2.5), (81, 1, "triangle", 0.5, 2.5), (77, 1, "triangle", 0.5, 2.5),
             (72, 1, "triangle", 0.5, 2.5), (76, 1, "triangle", 0.5, 2.5), (79, 1, "triangle", 0.5, 2.5), (84, 1, "triangle", 0.5, 2.5),
             (79, 1, "triangle", 0.5, 2.5), (74, 1, "triangle", 0.5, 2.5), (79, 1, "triangle", 0.5, 2.5), (83, 1, "triangle", 0.5, 2.5)],
            [(48, 4, "sine", 0.35, 1.0), (45, 4, "sine", 0.35, 1.0), (41, 4, "sine", 0.35, 1.0), (43, 4, "sine", 0.35, 1.0)],
        ],
    },
    "pond": {
        "bpm": 96,
        "layers": [
            [(69, 2, "sine", 0.45, 3.0), (72, 1, "sine", 0.45, 3.0), (74, 1, "sine", 0.45, 3.0), (76, 2, "sine", 0.45, 3.0),
             (72, 2, "sine", 0.45, 3.0), (69, 2, "sine", 0.45, 3.0), (67, 2, "sine", 0.45, 3.0), (64, 2, "sine", 0.45, 3.0),
             (62, 2, "sine", 0.45, 3.0)],
            [(57, 4, "triangle", 0.3, 1.5), (53, 4, "triangle", 0.3, 1.5), (50, 4, "triangle", 0.3, 1.5), (52, 4, "triangle", 0.3, 1.5)],
        ],
    },
    "shore": {
        "bpm": 112,
        "layers": [
            [(64, 1, "triangle", 0.45, 3.0), (67, 1, "triangle", 0.45, 3.0), (71, 1, "triangle", 0.45, 3.0), (67, 1, "triangle", 0.45, 3.0),
             (69, 1, "triangle", 0.45, 3.0), (72, 1, "triangle", 0.45, 3.0), (76, 1, "triangle", 0.45, 3.0), (72, 1, "triangle", 0.45, 3.0),
             (67, 1, "triangle", 0.45, 3.0), (71, 1, "triangle", 0.45, 3.0), (74, 1, "triangle", 0.45, 3.0), (71, 1, "triangle", 0.45, 3.0),
             (65, 1, "triangle", 0.45, 3.0), (69, 1, "triangle", 0.45, 3.0), (72, 1, "triangle", 0.45, 3.0), (69, 1, "triangle", 0.45, 3.0)],
            [(40, 2, "triangle", 0.35, 2.0), (40, 2, "triangle", 0.35, 2.0), (43, 2, "triangle", 0.35, 2.0), (43, 2, "triangle", 0.35, 2.0),
             (45, 2, "triangle", 0.35, 2.0), (45, 2, "triangle", 0.35, 2.0), (41, 2, "triangle", 0.35, 2.0), (41, 2, "triangle", 0.35, 2.0)],
        ],
    },
    "boat": {
        "bpm": 120,
        "layers": [
            [(60, 2, "square", 0.2, 4.0), (63, 2, "square", 0.2, 4.0), (67, 4, "square", 0.2, 4.0), (65, 2, "square", 0.2, 4.0),
             (63, 2, "square", 0.2, 4.0), (60, 2, "square", 0.2, 4.0), (None, 2, "square", 0.0, 0.0)],
            [(36, 1, "saw", 0.22, 6.0), (36, 1, "saw", 0.22, 6.0), (43, 1, "saw", 0.22, 6.0), (36, 1, "saw", 0.22, 6.0),
             (34, 1, "saw", 0.22, 6.0), (34, 1, "saw", 0.22, 6.0), (41, 1, "saw", 0.22, 6.0), (34, 1, "saw", 0.22, 6.0),
             (36, 1, "saw", 0.22, 6.0), (36, 1, "saw", 0.22, 6.0), (43, 1, "saw", 0.22, 6.0), (36, 1, "saw", 0.22, 6.0),
             (34, 1, "saw", 0.22, 6.0), (34, 1, "saw", 0.22, 6.0), (41, 1, "saw", 0.22, 6.0), (34, 1, "saw", 0.22, 6.0)],
        ],
    },
}


def note_freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def wave(kind, phase):
    """A waveform sample for a phase in cycles."""
    p = phase % 1.0
    if kind == "square":
        return 1.0 if p < 0.5 else -1.0
    if kind == "triangle":
        return 4 * abs(p - 0.5) - 1
    if kind == "saw":
        return 2 * p - 1
    return math.sin(2 * math.pi * p)


def tone(kind, freq, seconds, volume=1.0, decay=4.0):
    """A note that fades out, with a short release so it never clicks at the end."""
    n = int(RATE * seconds)
    step = freq / RATE
    release = max(1, int(0.02 * RATE))
    out = []
    for i in range(n):
        env = math.exp(-decay * i / RATE) * min(1.0, (n - i) / release)
        out.append(wave(kind, i * step) * volume * env)
    return out


def glide(kind, f0, f1, seconds, volume=1.0, decay=4.0):
    """A tone whose pitch slides from f0 to f1, for whooshes, bites and thumps."""
    n = int(RATE * seconds)
    release = max(1, int(0.01 * RATE))
    out = []
    phase = 0.0
    for i in range(n):
        freq = f0 + (f1 - f0) * i / max(1, n - 1)
        phase += freq / RATE
        env = math.exp(-decay * i / RATE) * min(1.0, (n - i) / release)
        out.append(wave(kind, phase) * volume * env)
    return out


def noise(seconds, volume=1.0, decay=6.0, smooth=0.2, seed=1):
    """Soft filtered noise, for splashes and whooshes."""
    rng = random.Random(seed)
    n = int(RATE * seconds)
    out = []
    last = 0.0
    for i in range(n):
        last += smooth * (rng.uniform(-1, 1) - last)
        out.append(last * volume * math.exp(-decay * i / RATE))
    return out


def mix(parts):
    """Lay several samples on top of each other, each starting at its own offset in seconds."""
    length = max(int(offset * RATE) + len(samples) for offset, samples in parts)
    buf = [0.0] * length
    for offset, samples in parts:
        start = int(offset * RATE)
        for i, s in enumerate(samples):
            buf[start + i] += s
    return buf


def to_sound(buf, volume):
    scale = 32767 * volume
    pcm = array("h", (int(max(-1.0, min(1.0, s)) * scale) for s in buf))
    return pygame.mixer.Sound(buffer=pcm.tobytes())


def render_track(track):
    beat = 60.0 / track["bpm"]
    total = None
    layers = []
    for layer in track["layers"]:
        samples = []
        for midi, beats, kind, volume, decay in layer:
            seconds = beats * beat
            if midi is None:
                samples.extend([0.0] * int(RATE * seconds))
            else:
                samples.extend(tone(kind, note_freq(midi), seconds, volume, decay))
        layers.append(samples)
        total = len(samples) if total is None else total
    buf = [0.0] * total
    for samples in layers:
        for i, s in enumerate(samples[:total]):
            buf[i] += s
    return buf


def build_effects():
    return {
        "cast": mix([(0, glide("sine", 700, 220, 0.3, 0.35, 6.0)), (0, noise(0.3, 0.3, 9.0, 0.5))]),
        "splash": mix([(0, noise(0.35, 0.6, 10.0, 0.25, seed=3)), (0, glide("sine", 520, 160, 0.18, 0.4, 12.0))]),
        "bite": mix([(0, glide("square", 880, 1320, 0.07, 0.25, 20.0)), (0.1, glide("square", 880, 1320, 0.07, 0.25, 20.0))]),
        "hookset": mix([(0, glide("square", 180, 60, 0.2, 0.6, 9.0)), (0, noise(0.03, 0.5, 60.0, 0.9, seed=5))]),
        "miss": glide("triangle", 320, 120, 0.3, 0.45, 5.0),
        "tug": glide("square", 120, 90, 0.12, 0.35, 12.0),
        "reel": glide("square", 1800, 1500, 0.02, 0.2, 60.0),
        "escape": glide("saw", 520, 90, 0.6, 0.3, 3.0),
        "catch": mix([(0, tone("triangle", note_freq(72), 0.12, 0.4, 6.0)), (0.09, tone("triangle", note_freq(76), 0.12, 0.4, 6.0)),
                      (0.18, tone("triangle", note_freq(79), 0.12, 0.4, 6.0)), (0.27, tone("triangle", note_freq(84), 0.3, 0.4, 5.0))]),
        "coin": mix([(0, tone("square", note_freq(88), 0.07, 0.25, 12.0)), (0.07, tone("square", note_freq(95), 0.12, 0.25, 10.0))]),
        "buy": mix([(0, tone("square", note_freq(76), 0.07, 0.25, 12.0)), (0.07, tone("square", note_freq(81), 0.12, 0.25, 10.0))]),
        "click": glide("square", 1200, 900, 0.03, 0.2, 40.0),
        "error": mix([(0, glide("square", 220, 180, 0.12, 0.3, 8.0)), (0.14, glide("square", 180, 140, 0.16, 0.3, 8.0))]),
        "plop": glide("sine", 480, 260, 0.12, 0.45, 18.0),
        "drag": glide("saw", 1100, 700, 0.28, 0.2, 3.0),
        "twitch": glide("square", 520, 380, 0.05, 0.25, 30.0),
        "jig": glide("triangle", 700, 480, 0.06, 0.3, 25.0),
        "snap": mix([(0, noise(0.08, 0.6, 40.0, 0.9, seed=9)), (0, glide("square", 400, 120, 0.1, 0.4, 20.0))]),
    }


class Sound:
    """Background music that follows the scene, and sound effects that play on events.

    If there is no audio device, every call quietly does nothing, so the game still runs."""

    def __init__(self):
        self.enabled = False
        self.muted = False
        self.music_name = None
        self.tracks = {}
        self.effects = {}
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=512)
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)  # Channel 0 is kept for the music
            self.music_channel = pygame.mixer.Channel(0)
            self.effects = {name: to_sound(buf, SFX_VOLUME) for name, buf in build_effects().items()}
            self.enabled = True
        except pygame.error:
            pass

    def set_music(self, name):
        if not self.enabled or name == self.music_name or name not in TRACKS:
            return
        self.music_name = name
        if name not in self.tracks:
            self.tracks[name] = to_sound(render_track(TRACKS[name]), MUSIC_VOLUME)
        self.music_channel.play(self.tracks[name], loops=-1)

    def play(self, name):
        if self.enabled and not self.muted and name in self.effects:
            self.effects[name].play()

    def toggle_mute(self):
        if not self.enabled:
            return
        self.muted = not self.muted
        if self.muted:
            pygame.mixer.pause()
        else:
            pygame.mixer.unpause()
