import pygame

from iso.sounds import Sound


class Audio:
    """The synthesised music and sound effects from iso/sounds.py, played through pygame's mixer.
    Panda3D draws the picture, and pygame only plays the sound. M mutes everything."""

    def __init__(self):
        # The mixer needs pygame initialised, but no window. Panda3D has its own window.
        pygame.init()
        self.sound = Sound()

    def set_music(self, name):
        self.sound.set_music(name)

    def play(self, name):
        self.sound.play(name)

    def toggle_mute(self):
        self.sound.toggle_mute()
        return self.sound.muted
