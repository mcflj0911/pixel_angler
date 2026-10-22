# The fight with a hooked fish, and the snag mini-game. Same numbers as the side-view game.
import random

from fish import move_toward

GAUGE_W = 360  # The fight gauge is this many pixels wide, and the HUD draws it as a fraction of that
TENSION_DECAY = 0.6
RUN_FRAMES = 20  # After a lunge, the fish is running hard for this many frames
SLACK_FRAMES = 150  # Frames of slack line, while the fish is calm, before the hook pulls free
LINE_DAMAGE_FROM = 70
SNAG_PULL_PROGRESS = 0.7  # Holding Up pulls the lure free this much each frame...
SNAG_PULL_TENSION = 1.4  # ...and tightens the line this much
SNAG_WIGGLE_PROGRESS = 12  # Each Left/Right wiggle that alternates sides
SNAG_WIGGLE_TENSION = 2
SNAG_WRONG_TENSION = 4  # Pressing the same side twice in a row only tightens the line
SNAG_TENSION_SNAP = 100  # The line snaps at this tension, and the lure is lost
SNAG_COOLDOWN = 90  # Once freed, the lure cannot snag again straight away


def frames(dt):
    return dt * 60


class Fight:
    """The fight gauge. A safe zone slides along the gauge with Left and Right, and the fish's marker wanders about it.
    Keep the marker in the zone to gain progress. Up pulls the line taut for tension, which snaps it at 100."""

    def __init__(self, swimmer, advantage, stats):
        self.swimmer = swimmer
        self.fish = swimmer["fish"]
        self.advantage = advantage  # +1 after a good hookset, -1 after a bad one
        self.progress = 30 + 12 * advantage
        self.tension = 0.0
        self.slack = 0
        self.zone_x = 0.0  # Left edge of the player's safe zone, in gauge pixels
        self.zone_vel = 0.0
        self.marker_x = GAUGE_W // 2
        self.target_x = GAUGE_W // 2
        self.timer = 0
        self.tug = 0.0  # Decays after each lunge of the fish
        self.clutch = 1.0  # Drag setting: higher pulls the fish in faster, but spikes the line
        self.stamina = 100.0
        self.tired = False
        self.ticks = 0
        self.last_lunge = -999
        self.lunge_shake = 0.0
        self.shake = 0.0  # How hard the rod trembles, which the camera turns into a shake
        self.lunge_sound = False  # Set on the frame the fish lunges, so the game can play the reel's drag sound
        self.stats = stats

    def update(self, dt, keys, economy):
        """Runs one step of the fight. Returns 'land', 'lost', 'snapped' or None while it goes on.
        keys: a dict with left, right and up booleans."""
        fish = self.fish
        f = frames(dt)
        self.ticks += f
        if self.update_tension(dt, keys, economy):
            return "snapped" if self.tension >= 100 else "lost"

        # Left and right push the safe zone along the gauge, with a little momentum
        push = (1 if keys["right"] else 0) - (1 if keys["left"] else 0)
        self.zone_vel += 1.2 * push * f
        self.zone_vel *= 0.85 ** f  # Friction
        self.zone_x += self.zone_vel * f
        self.zone_x = max(0, min(GAUGE_W - fish.zone_size, self.zone_x))

        # Fish marker AI: pick a new target every so often, then glide towards it
        self.timer -= f
        if self.timer <= 0:
            self.target_x = random.randint(0, GAUGE_W)
            self.timer = random.randint(*fish.aggression)
        self.marker_x = move_toward(self.marker_x, self.target_x, fish.fish_speed * (0.5 if self.tired else 1) * f)

        # Every so often the fish lunges, which shakes the rod. A bad hookset means harder lunges.
        if self.ticks % 40 < f:
            strain = 1 + 0.25 * max(0.0, fish.weight - self.stats["rating"])
            self.tug = (1 + fish.weight) * strain / self.stats["drag"] * (1.3 if self.advantage < 0 else 1) * (0.5 if self.tired else 1)
            self.lunge_shake = max(self.lunge_shake, self.tug * 0.8)
            self.last_lunge = self.ticks
            economy.wear_part("line", 0.1 * fish.weight)
            economy.wear_part("rod", 0.8 if strain > 1 else 0.1)
            self.lunge_sound = True
        else:
            self.lunge_sound = False

        # Progress: gain while the marker is in the safe zone, lose otherwise
        if self.zone_x <= self.marker_x <= self.zone_x + fish.zone_size:
            gain = 0.35 * self.stats["power"] * self.clutch
            self.progress += gain * (1 + 0.15 * self.advantage) * f
        else:
            self.progress -= 0.25 * (1 - 0.15 * self.advantage) * f

        if self.progress >= 100:
            return "land"
        if self.progress <= 0:
            return "lost"
        return None

    def update_tension(self, dt, keys, economy):
        """Reeling while the fish runs spikes the line. Going slack for too long lets the hook pull free.
        Returns True when the fight is over (the line snapped or the hook pulled free)."""
        f = frames(dt)
        fish = self.fish
        load = fish.weight / self.stats["strength"]
        running = self.ticks - self.last_lunge < RUN_FRAMES
        if running:
            self.stamina = max(0.0, self.stamina - 0.5 * fish.weight / 3 * f)
        else:
            self.stamina = min(100.0, self.stamina + 0.2 * f)
        self.tired = self.stamina < 30
        if keys["up"]:
            self.tension += load * (1.6 if running else 0.5) * self.clutch ** 1.2 * f
            self.slack = 0
            if not running:
                self.progress += 0.08 * self.stats["speed"] * self.clutch * f  # Winding in while the fish rests gains line
        elif running:
            self.tension += load * 0.6 * (0.5 if self.tired else 1) * f  # The fish pulls the line tight, less when tired
        else:
            self.tension = max(0.0, self.tension - TENSION_DECAY * f)  # Letting go slackens the line
            self.slack = self.slack + f if self.tension < 20 else 0
        self.tension = min(100.0, self.tension)
        self.shake = max(0.0, (self.tension - 75) / 8)  # The rod trembles near the snapping point

        return self.tension >= 100 or self.slack > SLACK_FRAMES


class Snag:
    """A lure caught on a stump. Wiggle Left and Right alternately to free it. Holding Up pulls harder and tightens the line."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.progress = 0.0
        self.tension = 0.0
        self.side = 0  # Which side the last wiggle was on, so the next one must alternate
        self.cooldown = 0

    def wiggle(self, side, sound):
        if side != self.side:
            self.progress += SNAG_WIGGLE_PROGRESS
            self.tension += SNAG_WIGGLE_TENSION
            sound("twitch")
        else:
            self.tension += SNAG_WRONG_TENSION
        self.side = side

    def update(self, dt, up, power, economy):
        """Returns 'freed', 'snapped' or None while it goes on."""
        f = frames(dt)
        if up:
            self.progress += SNAG_PULL_PROGRESS * power * f
            self.tension += SNAG_PULL_TENSION * f
        else:
            self.progress = max(0.0, self.progress - 0.2 * f)
            self.tension = max(0.0, self.tension - 0.5 * f)
        economy.wear_part("line", 0.005 * f)  # Rubbing on the snag frays the line
        self.tension = min(100.0, self.tension)
        if self.progress >= 100:
            economy.wear_part("line", 4)
            economy.wear_part("hook", 2)
            return "freed"
        if self.tension >= SNAG_TENSION_SNAP:
            return "snapped"
        return None
