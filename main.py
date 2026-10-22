import sys

import pygame

from config import WIDTH, HEIGHT, FPS, UI_WIDTH
from ui import draw_backdrop, get_backdrop

SIDE = (WIDTH - UI_WIDTH) // 2  # Empty space either side of the menus
from economy import Economy
from scenes import TitleScene
from sound import Sound
from weather import Weather, DAY_FRAMES


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Pixel Fishing")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)
        self.large_font = pygame.font.SysFont(None, 72)
        self.economy = Economy()
        self.sound = Sound()
        self.weather = Weather()  # Shared by every scene, so the weather keeps changing on the menus too
        self.running = True
        self.canvas = pygame.Surface((UI_WIDTH, HEIGHT))  # Menus are drawn here, then centred on the screen
        self.ticks = 0
        self.scenes = [TitleScene(self)]

    # The scene on top of the stack gets the input and is drawn
    def open(self, scene):
        self.scenes.append(scene)

    def close(self):
        self.scenes.pop()

    def switch(self, scene):
        self.scenes[-1] = scene

    def to_canvas(self, event):
        """Mouse positions on the full screen, moved into the menu canvas."""
        if not hasattr(event, "pos"):
            return event
        x, y = event.pos
        return pygame.event.Event(event.type, dict(event.dict, pos=(x - SIDE, y)))

    def draw_scene(self, scene):
        if scene.full_width:
            scene.draw(self.screen)
            return
        # The sky fills the sides, and the menu sits in the middle
        self.screen.blit(get_backdrop(), (0, 0))
        draw_backdrop(self.screen, self.ticks)
        self.canvas.fill((0, 0, 0))
        scene.draw(self.canvas)
        self.screen.blit(self.canvas, (SIDE, 0))

    def run(self):
        while self.running and self.scenes:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                    self.sound.toggle_mute()  # M mutes or unmutes everything, from any screen
                elif self.scenes:
                    scene = self.scenes[-1]
                    scene.handle_event(event if scene.full_width else self.to_canvas(event))

            if not self.scenes:
                break
            scene = self.scenes[-1]
            self.sound.set_music(scene.music)
            self.weather.update()
            self.economy.new_day(self.weather.clock // DAY_FRAMES)
            self.ticks += 1
            scene.update()
            self.draw_scene(scene)
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


def main():
    App().run()


if __name__ == "__main__":
    main()
