"""The sounds of the isometric game: the line zipping out and the splash of the cast, the rod knocking and the reel ratchet,
the surf and the gulls, the frogs and birds of the pond, the boat bell, and the shops. Everything is synthesised here, so
the game needs no audio files. The synth primitives are the ones the side-view game uses (sound.py).

Each area has its own music, with a bed underneath that matches the place: birds and frogs by the pond, surf and gulls on
the shore, the slow swell out on the open sea, and a light tune for walking about the town."""
import math
import random

import pygame

from sound import RATE, MUSIC_VOLUME, SFX_VOLUME, glide, mix, noise, note_freq, render_track, tone, to_sound

BED_VOLUME = 0.5  # How loud the ambient bed is under the music

# Each track: bpm, layers of (midi note or None, beats, wave, volume, decay), and the bed under it.
TRACKS = {
    "menu": {
        "bpm": 80, "bed": None,
        "layers": [
            [(60, 4, "sine", 0.25, 1.5), (57, 4, "sine", 0.25, 1.5), (53, 4, "sine", 0.25, 1.5), (55, 4, "sine", 0.25, 1.5)],
            [(72, 1, "triangle", 0.3, 4.0), (76, 1, "triangle", 0.3, 4.0), (79, 1, "triangle", 0.3, 4.0), (76, 1, "triangle", 0.3, 4.0)] * 4,
        ],
    },
    "town": {
        "bpm": 100, "bed": None,
        "layers": [
            [(64, 2, "triangle", 0.3, 3.0), (67, 1, "triangle", 0.3, 3.0), (69, 1, "triangle", 0.3, 3.0), (67, 2, "triangle", 0.3, 3.0),
             (65, 2, "triangle", 0.3, 3.0), (64, 2, "triangle", 0.3, 3.0), (62, 2, "triangle", 0.3, 3.0), (60, 4, "triangle", 0.3, 3.0)],
            [(48, 4, "triangle", 0.2, 1.5), (45, 4, "triangle", 0.2, 1.5), (41, 4, "triangle", 0.2, 1.5), (43, 4, "triangle", 0.2, 1.5)],
        ],
    },
    "pond": {
        "bpm": 92, "bed": "pond",
        "layers": [
            [(69, 2, "triangle", 0.4, 6.0), (72, 1, "triangle", 0.4, 6.0), (74, 1, "triangle", 0.4, 6.0), (76, 2, "triangle", 0.4, 6.0),
             (72, 2, "triangle", 0.4, 6.0), (69, 2, "triangle", 0.4, 6.0), (67, 2, "triangle", 0.4, 6.0), (64, 2, "triangle", 0.4, 6.0),
             (62, 2, "triangle", 0.4, 6.0)],
            [(57, 4, "sine", 0.25, 1.5), (53, 4, "sine", 0.25, 1.5), (50, 4, "sine", 0.25, 1.5), (52, 4, "sine", 0.25, 1.5)],
        ],
    },
    "shore": {
        "bpm": 108, "bed": "surf",
        "layers": [
            [(64, 1, "triangle", 0.35, 4.0), (67, 1, "triangle", 0.35, 4.0), (71, 1, "triangle", 0.35, 4.0), (67, 1, "triangle", 0.35, 4.0),
             (69, 1, "triangle", 0.35, 4.0), (72, 1, "triangle", 0.35, 4.0), (76, 1, "triangle", 0.35, 4.0), (72, 1, "triangle", 0.35, 4.0),
             (67, 1, "triangle", 0.35, 4.0), (71, 1, "triangle", 0.35, 4.0), (74, 1, "triangle", 0.35, 4.0), (71, 1, "triangle", 0.35, 4.0),
             (65, 1, "triangle", 0.35, 4.0), (69, 1, "triangle", 0.35, 4.0), (72, 1, "triangle", 0.35, 4.0), (69, 1, "triangle", 0.35, 4.0)],
            [(40, 4, "triangle", 0.3, 2.0), (43, 4, "triangle", 0.3, 2.0), (45, 4, "triangle", 0.3, 2.0), (41, 4, "triangle", 0.3, 2.0)],
        ],
    },
    "boat": {
        "bpm": 66, "bed": "sea",
        "layers": [
            [(60, 4, "sine", 0.3, 1.2), (64, 4, "sine", 0.3, 1.2), (67, 4, "sine", 0.3, 1.2), (65, 4, "sine", 0.3, 1.2)],
            [(36, 8, "sine", 0.25, 0.8), (34, 8, "sine", 0.25, 0.8)],
        ],
    },
}


def event_bed(seconds, rate, make, seed):
    """Scatters short sounds (a chirp, a frog, a whistle) at random times through the loop."""
    rng = random.Random(seed)
    n = int(RATE * seconds)
    buf = [0.0] * n
    for _ in range(int(seconds * rate)):
        start = int(rng.uniform(0, seconds - 0.5) * RATE)
        for i, s in enumerate(make(rng)):
            if start + i < n:
                buf[start + i] += s
    return buf


def sea_bed(seconds, volume, waves, seed):
    """Wash of the sea: soft noise that swells and falls. waves is how many swells fit in the loop, so it joins up."""
    base = noise(seconds, volume, 0.0, 0.03, seed=seed)
    n = len(base)
    return [s * (0.55 + 0.45 * math.sin(2 * math.pi * waves * i / n)) for i, s in enumerate(base)]


def bed_for(name, seconds):
    """The ambient bed for a track, as a sample buffer exactly as long as the music."""
    if name == "pond":
        return event_bed(seconds, 0.6, lambda rng: glide("square", 190, 150, 0.09, 0.08, 30.0), 32)  # Frogs only, no chirps
    if name == "surf":
        waves = sea_bed(seconds, BED_VOLUME * 0.6, max(1, round(seconds / 4)), 34)
        gulls = event_bed(seconds, 0.3, lambda rng: glide("sine", 1500, 1950, 0.35, 0.1, 4.0), 35)
        return [a + b for a, b in zip(waves, gulls)]
    if name == "sea":
        waves = sea_bed(seconds, BED_VOLUME, max(1, round(seconds / 6)), 36)
        whistles = event_bed(seconds, 0.15, lambda rng: glide("sine", 1800, 2600, 0.5, 0.08, 3.0), 37)
        return [a + b for a, b in zip(waves, whistles)]
    return None


def render_music(track):
    """The music for a track, with its bed mixed underneath."""
    buf = render_track(track)
    bed = bed_for(track["bed"], len(buf) / RATE) if track.get("bed") else None
    if bed:
        buf = [a + b for a, b in zip(buf, bed)]
    return buf


def build_effects():
    return {
        # The cast: the line whips out over the water with a hiss, then the lure lands with a splash
        "cast": mix([(0, glide("sine", 900, 260, 0.28, 0.25, 7.0)), (0, noise(0.3, 0.35, 9.0, 0.35, seed=12)),
                     (0.02, glide("triangle", 1600, 400, 0.12, 0.15, 14.0))]),
        "splash": mix([(0, noise(0.4, 0.55, 8.0, 0.2, seed=3)), (0.02, glide("sine", 260, 90, 0.22, 0.25, 10.0))]),
        "plop": mix([(0, glide("sine", 380, 180, 0.1, 0.35, 20.0)), (0, noise(0.04, 0.25, 50.0, 0.8, seed=6))]),
        # The reel: a ratchet of clicks while the line comes in
        "reel": mix([(0, noise(0.012, 0.5, 80.0, 0.9, seed=4)), (0, glide("square", 2400, 1800, 0.01, 0.12, 80.0))]),
        # Line screaming off the reel when a fish runs
        "drag": mix([(0, glide("saw", 900, 600, 0.3, 0.16, 2.5)), (0, noise(0.3, 0.12, 3.0, 0.5, seed=8))]),
        # A bite is a knock on the rod tip, twice
        "bite": mix([(0, noise(0.02, 0.6, 90.0, 0.9, seed=10)), (0, glide("square", 300, 220, 0.05, 0.3, 40.0)),
                     (0.12, noise(0.02, 0.6, 90.0, 0.9, seed=11)), (0.12, glide("square", 300, 220, 0.05, 0.3, 40.0))]),
        # Striking: a sharp thunk, and the line going tight
        "hookset": mix([(0, glide("square", 140, 60, 0.2, 0.55, 9.0)), (0, noise(0.04, 0.7, 50.0, 0.9, seed=5))]),
        "twitch": glide("triangle", 620, 400, 0.05, 0.25, 25.0),
        "jig": glide("triangle", 560, 340, 0.07, 0.3, 22.0),
        "tug": glide("square", 110, 80, 0.12, 0.3, 12.0),
        "miss": glide("triangle", 340, 180, 0.3, 0.4, 5.0),
        "snap": mix([(0, noise(0.06, 0.8, 50.0, 0.95, seed=7)), (0, glide("saw", 600, 200, 0.12, 0.3, 15.0))]),
        "escape": glide("saw", 500, 120, 0.6, 0.2, 3.0),
        # A catch: a flop on the boards, then a rising fanfare
        "catch": mix([(0, noise(0.08, 0.4, 30.0, 0.8, seed=9)),
                      (0.1, tone("triangle", note_freq(76), 0.12, 0.35, 6.0)), (0.19, tone("triangle", note_freq(79), 0.12, 0.35, 6.0)),
                      (0.28, tone("triangle", note_freq(83), 0.12, 0.35, 6.0)), (0.37, tone("triangle", note_freq(88), 0.3, 0.35, 5.0))]),
        "click": mix([(0, noise(0.01, 0.5, 100.0, 0.95, seed=13)), (0, glide("triangle", 900, 900, 0.02, 0.2, 40.0))]),
        "buy": mix([(0, tone("square", note_freq(76), 0.07, 0.2, 12.0)), (0.07, tone("square", note_freq(81), 0.12, 0.2, 10.0))]),
        "bell": mix([(0, tone("triangle", note_freq(84), 0.6, 0.35, 3.0)), (0.25, tone("triangle", note_freq(88), 0.8, 0.3, 2.0))]),
        "error": mix([(0, glide("square", 200, 160, 0.12, 0.25, 8.0)), (0.14, glide("square", 160, 120, 0.16, 0.25, 8.0))]),
    }


class Sound:
    """Music that follows the place, and sound effects that play on events. With no audio device every call does nothing."""

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
            self.tracks[name] = to_sound(render_music(TRACKS[name]), MUSIC_VOLUME)
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
