import pygame
import random
import math

# --- CONFIGURATION & CONSTANTS ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 700
PANE_LEFT_WIDTH, PANE_RIGHT_WIDTH = 250, 250
GAME_AREA_WIDTH = SCREEN_WIDTH - PANE_LEFT_WIDTH - PANE_RIGHT_WIDTH

# Fishing Balance
MAX_FISH = 25
SPAWN_INTERVAL = 2000
BITE_RADIUS = 55
MAX_CAST_DIST = 550
WEATHER_CYCLE_MS = 180000  # 3 Minutes

# Colors
WHITE, BLACK, GRAY, DARK_GRAY = (255, 255, 255), (0, 0, 0), (40, 40, 40), (25, 25, 25)
YELLOW, ORANGE, RED, CYAN, BROWN = (255, 223, 0), (255, 140, 0), (255, 50, 50), (0, 255, 255), (139, 69, 19)

# Weather Tones
WATER_SUNNY = (30, 80, 160)
WATER_WINDY = (45, 95, 140)
WATER_RAINY = (20, 45, 80)

# States
WALKING, CHARGING, WAITING, BITING, REELING = 0, 1, 2, 3, 4
SUNNY, WINDY, RAINY = "SUNNY", "WINDY", "RAINY"


# --- PARTICLE CLASSES ---

class Bubble:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        self.vel = pygame.math.Vector2(random.uniform(-0.3, 0.3), random.uniform(-0.8, -1.5))
        self.life = 255
        self.size = random.randint(1, 3)

    def update(self):
        self.pos += self.vel
        self.life -= 4
        return self.life > 0

    def draw(self, screen):
        alpha_color = (self.life, self.life, 255)
        pygame.draw.rect(screen, alpha_color, (int(self.pos.x), int(self.pos.y), self.size, self.size))


class Ripple:
    def __init__(self, x, y, size=5):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = size
        self.life = 255

    def update(self):
        self.radius += 0.9
        self.life -= 5
        return self.life > 0

    def draw(self, screen):
        alpha = max(0, self.life)
        col = (100, 150, 255)
        pygame.draw.circle(screen, col, (int(self.pos.x), int(self.pos.y)), int(self.radius), 1)


# --- FISH SPRITE ---

class FishSprite(pygame.sprite.Sprite):
    def __init__(self, data):
        super().__init__()
        self.name, self.color = data['name'], pygame.Color(data['color'])
        self.weight = round(random.uniform(float(data['min_w']), float(data['max_w'])), 2)
        self.price = int(data['price'])

        self.pos = pygame.math.Vector2(random.randint(300, 900), random.randint(100, 600))
        self.velocity = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.max_speed = random.uniform(0.6, 1.2)
        self.wander_angle = random.uniform(0, 360)
        self.current_angle = self.velocity.angle_to(pygame.math.Vector2(1, 0))

        self.p_size = 4 if self.weight < 12 else 5
        self.is_hooked = False
        self.submerged = False
        self.image = pygame.Surface((64, 64), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.wiggle_timer = random.uniform(0, 10)

    def draw_fish_frame(self, wiggle_offset):
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        s, mid = self.p_size, 32
        c = self.color
        if self.submerged:
            c = (c.r // 3, c.g // 3, c.b // 3)  # Darken for submerged look

        dark_c = (max(0, c[0] - 60), max(0, c[1] - 60), max(0, c[2] - 60))
        pygame.draw.rect(surf, dark_c, (mid + s // 2, mid - s * 2, s, s))  # Top Fin
        pygame.draw.rect(surf, dark_c, (mid + s // 2, mid + s, s, s))  # Bottom Fin
        pygame.draw.rect(surf, dark_c, (mid + s * 2, mid - s, s, s * 2))  # Head
        pygame.draw.rect(surf, WHITE, (mid + s * 2 + s // 2, mid - s // 2, 2, 2)) if not self.submerged else None
        pygame.draw.rect(surf, c, (mid, mid - s, s * 2, s * 2))  # Body
        pygame.draw.rect(surf, c, (mid - s, mid - s // 2, s, s))  # Tail Base
        pygame.draw.rect(surf, dark_c, (mid - s * 2, (mid - s) + wiggle_offset, s, s * 2))  # Tail
        return surf

    def update(self, weather):
        if weather == RAINY:
            if random.random() < 0.005: self.submerged = not self.submerged
        else:
            self.submerged = False

        speed_mult = 5 if self.is_hooked else self.velocity.length() * 1.5
        self.wiggle_timer += 0.1 * speed_mult
        wiggle_offset = math.sin(self.wiggle_timer) * (self.p_size * 0.7)

        if not self.is_hooked:
            self.wander_angle += random.uniform(-4, 4)
            steer = pygame.math.Vector2(1, 0).rotate(self.wander_angle)
            margin = 85
            if self.pos.x < PANE_LEFT_WIDTH + margin:
                steer.x += 1.2
            elif self.pos.x > (SCREEN_WIDTH - PANE_RIGHT_WIDTH) - margin:
                steer.x -= 1.2
            if self.pos.y < 80:
                steer.y += 1.2
            elif self.pos.y > SCREEN_HEIGHT - 80:
                steer.y -= 1.2

            self.velocity += steer
            if self.velocity.length_squared() > 0.1:
                self.velocity.scale_to_length(self.max_speed)
                target_angle = self.velocity.angle_to(pygame.math.Vector2(1, 0))
                angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
                self.current_angle += angle_diff * 0.08
                self.pos += self.velocity
                self.image = pygame.transform.rotate(self.draw_fish_frame(wiggle_offset), self.current_angle)
            else:
                self.image = pygame.transform.rotate(self.draw_fish_frame(wiggle_offset), self.current_angle)
        else:
            struggle = math.sin(self.wiggle_timer * 2) * 25
            self.image = pygame.transform.rotate(self.draw_fish_frame(wiggle_offset), 90 + struggle)
        self.rect.center = self.pos


# --- MAIN GAME CLASS ---

class FishingGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Ferdinand's Saltwater Angler - Weather Update")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 14)
        self.header = pygame.font.SysFont("monospace", 18, bold=True)

        # Weather System Init
        self.weather = random.choice([SUNNY, WINDY, RAINY])
        self.weather_timer = pygame.time.get_ticks()
        self.wind_vector = pygame.math.Vector2(0, 0)

        self.player_y = SCREEN_HEIGHT // 2
        self.gold, self.basket, self.log = 0, [], ["Angler Log Online..."]
        self.fish_group = pygame.sprite.Group()
        self.bubbles, self.ripples = [], []
        self.last_spawn_time = 0
        self.state = WALKING
        self.bobber_pos = pygame.math.Vector2(0, 0)
        self.active_fish = None
        self.line_tension, self.cast_power, self.power_dir = 0, 0, 1

        self.fish_db = [
            {'name': 'Trevally', 'min_w': '12', 'max_w': '40', 'price': '900', 'color': 'cyan'},
            {'name': 'Grouper', 'min_w': '8', 'max_w': '22', 'price': '500', 'color': 'orange'},
            {'name': 'Milkfish', 'min_w': '2', 'max_w': '8', 'price': '200', 'color': 'white'}
        ]

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 25: self.log.pop(0)

    def reset_fishing(self, escaped=False):
        if self.active_fish:
            self.active_fish.is_hooked = False
            if escaped: self.active_fish.max_speed *= 2
        self.state, self.active_fish, self.line_tension, self.cast_power = WALKING, None, 0, 0

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if self.state == WALKING:
            if keys[pygame.K_w] and self.player_y > 40: self.player_y -= 5
            if keys[pygame.K_s] and self.player_y < SCREEN_HEIGHT - 40: self.player_y += 5

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q: self.reset_fishing(True if self.state == REELING else False)
                if event.key == pygame.K_SPACE:
                    if self.state == WALKING:
                        self.state = CHARGING; self.cast_power = 0
                    elif self.state == REELING:
                        self.ripples.append(Ripple(self.bobber_pos.x, self.bobber_pos.y, 10))
                        reel_p = 15 / (self.active_fish.weight * 0.15 + 1)
                        self.bobber_pos.x += reel_p
                        self.line_tension += (self.active_fish.weight * 0.18)
                if event.key == pygame.K_e and self.state == BITING:
                    self.state = REELING;
                    self.active_fish.is_hooked = True;
                    self.line_tension = 30
                    self.ripples.append(Ripple(self.bobber_pos.x, self.bobber_pos.y, 40))
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE and self.state == CHARGING:
                    dock_x = SCREEN_WIDTH - PANE_RIGHT_WIDTH - 20
                    self.bobber_pos = pygame.math.Vector2(dock_x - (self.cast_power / 100) * MAX_CAST_DIST,
                                                          self.player_y)
                    self.state = WAITING
                    self.ripples.append(Ripple(self.bobber_pos.x, self.bobber_pos.y, 25))
        return True

    def update(self):
        now = pygame.time.get_ticks()

        # Weather Cycle Check (3 mins)
        if now - self.weather_timer > WEATHER_CYCLE_MS:
            self.weather = random.choice([SUNNY, WINDY, RAINY])
            self.weather_timer = now
            self.add_log(f"Weather changed to {self.weather}")
            self.wind_vector = pygame.math.Vector2(random.uniform(-0.8, 0.8), random.uniform(-0.3,
                                                                                             0.3)) if self.weather == WINDY else pygame.math.Vector2(
                0, 0)

        # Spawning
        if now - self.last_spawn_time > SPAWN_INTERVAL and len(self.fish_group) < MAX_FISH:
            self.fish_group.add(FishSprite(random.choice(self.fish_db)))
            self.last_spawn_time = now

        self.fish_group.update(self.weather)

        # Particles
        for f in self.fish_group:
            if random.random() < 0.015: self.bubbles.append(Bubble(f.pos.x, f.pos.y))
            if random.random() < 0.004: self.ripples.append(Ripple(f.pos.x, f.pos.y, random.randint(3, 8)))

        if self.weather == RAINY and random.random() < 0.08:
            self.ripples.append(Ripple(random.randint(PANE_LEFT_WIDTH, SCREEN_WIDTH - PANE_RIGHT_WIDTH),
                                       random.randint(0, SCREEN_HEIGHT), 2))

        self.bubbles = [b for b in self.bubbles if b.update()]
        self.ripples = [r for r in self.ripples if r.update()]

        # Physics/State Logic
        if self.state in [WAITING, BITING, REELING]:
            self.bobber_pos += self.wind_vector

        if self.state == CHARGING:
            self.cast_power += 2.5 * self.power_dir
            if self.cast_power >= 100 or self.cast_power <= 0: self.power_dir *= -1

        elif self.state == WAITING:
            if random.random() < 0.01: self.ripples.append(Ripple(self.bobber_pos.x, self.bobber_pos.y, 6))
            for fish in self.fish_group:
                if not fish.submerged and self.bobber_pos.distance_to(
                        fish.pos) < BITE_RADIUS and random.random() < 0.02:
                    self.state, self.active_fish, self.bite_timer = BITING, fish, now + 1500
                    self.add_log("FISH ON! Press 'E'!")
                    break

        elif self.state == REELING:
            surge = (math.sin(now * 0.0015) + 1) * (self.active_fish.weight * 0.12)
            # Wind friction if blowing away
            wind_penalty = abs(self.wind_vector.x) * 0.4 if self.wind_vector.x < 0 else 0
            self.line_tension = max(0, self.line_tension - 0.75 + surge + wind_penalty)
            self.bobber_pos.x -= (surge * 0.2)
            self.active_fish.pos = pygame.math.Vector2(self.bobber_pos.x, self.bobber_pos.y)

            if self.line_tension > 100:
                self.reset_fishing(True); self.add_log("SNAP! Line broke.")
            elif self.bobber_pos.x >= SCREEN_WIDTH - PANE_RIGHT_WIDTH - 35:
                self.basket.append({"name": self.active_fish.name, "weight": self.active_fish.weight})
                self.gold += self.active_fish.price
                self.active_fish.kill();
                self.reset_fishing();
                self.add_log(f"Land {self.basket[-1]['name']}!")

    def draw_gui(self):
        # 3/4 ANGLER'S LOG (TOP)
        pygame.draw.rect(self.screen, DARK_GRAY, (0, 0, PANE_LEFT_WIDTH, 500))
        self.screen.blit(self.header.render("ANGLER'S LOG", True, CYAN), (20, 20))
        y = 60
        for msg in reversed(self.log):
            if y > 460: break
            line = ""
            for word in msg.split(' '):
                if self.font.size(line + word)[0] < PANE_LEFT_WIDTH - 40:
                    line += word + " "
                else:
                    self.screen.blit(self.font.render(line, True, WHITE), (15, y));
                    y += 18;
                    line = word + " "
            self.screen.blit(self.font.render(line, True, WHITE), (15, y));
            y += 22

        # 1/4 FORECAST (BOTTOM)
        pygame.draw.rect(self.screen, (15, 15, 15), (0, 500, PANE_LEFT_WIDTH, 200))
        pygame.draw.line(self.screen, GRAY, (0, 500), (PANE_LEFT_WIDTH, 500), 2)
        self.screen.blit(self.header.render("WEATHER FORECAST", True, YELLOW), (20, 515))
        self.screen.blit(self.font.render(f"SYSTEM: {self.weather}", True, WHITE), (20, 545))
        if self.weather == WINDY:
            self.screen.blit(self.font.render(f"WIND: {abs(self.wind_vector.x * 15):.1f} kts", True, WHITE), (20, 565))
        elif self.weather == RAINY:
            self.screen.blit(self.font.render("FISH ARE SUBMERGING", True, ORANGE), (20, 565))

        # STATS PANE (RIGHT)
        pygame.draw.rect(self.screen, DARK_GRAY, (SCREEN_WIDTH - PANE_RIGHT_WIDTH, 0, PANE_RIGHT_WIDTH, SCREEN_HEIGHT))
        self.screen.blit(self.header.render("FISHING STATS", True, CYAN), (SCREEN_WIDTH - PANE_RIGHT_WIDTH + 20, 20))
        self.screen.blit(self.font.render(f"Gold: {self.gold}", True, YELLOW),
                         (SCREEN_WIDTH - PANE_RIGHT_WIDTH + 20, 60))
        self.screen.blit(self.font.render("--- BASKET ---", True, WHITE), (SCREEN_WIDTH - PANE_RIGHT_WIDTH + 20, 100))
        for i, item in enumerate(self.basket[-12:]):
            self.screen.blit(self.font.render(f"> {item['name']} ({item['weight']}kg)", True, WHITE),
                             (SCREEN_WIDTH - PANE_RIGHT_WIDTH + 20, 130 + i * 22))

        # TENSION GAUGE
        if self.state == REELING:
            gx, gy, gw = SCREEN_WIDTH - PANE_RIGHT_WIDTH + 20, 480, PANE_RIGHT_WIDTH - 40
            label_col = RED if self.line_tension > 75 else WHITE
            self.screen.blit(self.font.render("LINE TENSION", True, label_col), (gx, gy - 20))
            pygame.draw.rect(self.screen, (60, 20, 20), (gx, gy, gw, 15))
            pygame.draw.rect(self.screen, RED if self.line_tension > 80 else ORANGE,
                             (gx, gy, (self.line_tension / 100) * gw, 15))
            pygame.draw.rect(self.screen, WHITE, (gx, gy, gw, 15), 1)

    def draw(self):
        now = pygame.time.get_ticks()
        # Water Texture Base
        base_water = WATER_SUNNY if self.weather == SUNNY else WATER_WINDY if self.weather == WINDY else WATER_RAINY
        shimmer = math.sin(now * 0.001) * 8
        self.screen.fill(BLACK)
        pygame.draw.rect(self.screen, (base_water[0], base_water[1], int(base_water[2] + shimmer)),
                         (PANE_LEFT_WIDTH, 0, GAME_AREA_WIDTH, SCREEN_HEIGHT))

        # Water Grain/Texture
        for _ in range(12):
            tx, ty = random.randint(PANE_LEFT_WIDTH, SCREEN_WIDTH - PANE_RIGHT_WIDTH), random.randint(0, SCREEN_HEIGHT)
            pygame.draw.rect(self.screen,
                             (min(255, base_water[0] + 20), min(255, base_water[1] + 20), min(255, base_water[2] + 20)),
                             (tx, ty, 3, 1))

        # Entities
        for b in self.bubbles: b.draw(self.screen)
        for r in self.ripples: r.draw(self.screen)
        self.fish_group.draw(self.screen)

        # Player & Bobber
        dock_x = SCREEN_WIDTH - PANE_RIGHT_WIDTH - 20
        pygame.draw.rect(self.screen, BROWN, (dock_x, 0, 30, SCREEN_HEIGHT))
        pygame.draw.rect(self.screen, (210, 180, 140), (dock_x + 5, self.player_y - 15, 10, 30))

        if self.state == CHARGING:
            pygame.draw.rect(self.screen, WHITE,
                             (int(dock_x - (self.cast_power / 100) * MAX_CAST_DIST), self.player_y, 6, 6), 1)

        if self.state in [WAITING, BITING, REELING]:
            shk = random.uniform(-1, 1) * (self.line_tension / 18) if self.state == REELING else 0
            bob_y = self.bobber_pos.y + math.sin(now * 0.005) * 5
            pygame.draw.line(self.screen, WHITE, (dock_x, self.player_y), (self.bobber_pos.x, bob_y + shk), 1)
            pygame.draw.rect(self.screen, RED if self.state == BITING else YELLOW,
                             (self.bobber_pos.x - 4, bob_y - 4 + shk, 8, 8))

        self.draw_gui()
        pygame.display.flip()

    def run(self):
        while self.handle_input(): self.update(); self.draw(); self.clock.tick(60)
        pygame.quit()


if __name__ == "__main__":
    FishingGame().run()