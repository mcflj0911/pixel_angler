"""Errands: trips about the town for anyone with a body. Someone may walk to a bench or deckchair and rest on it, or to a shop
counter and buy something, and then walk back. The anglers and the townsfolk both go on errands, and share this code.
Whoever uses the Errands mixin must have a level, a position (x, y and tile), a node and a body, and calls init_errands."""
import math
import random

WALK_PACE = 1.2  # Tiles a second as they walk about the town
SEAT_CHANCE = 0.35  # Chance that a stop ends with a rest on a seat
SHOP_CHANCE = 0.25  # Chance that it ends with a trip to a shop counter, otherwise they carry on as normal
SEAT_RANGE = 25  # Tiles within which someone will walk to a seat
SIT_TIME = (40.0, 90.0)  # Seconds someone rests on a seat
BUY_TIME = 5.0  # Seconds someone stays at the counter
CLERK_REPLY = 2.0  # Seconds after they ask before the clerk answers
BENCH_DROP = -0.22  # How far a seated person sinks on a bench, so the hips sit on its seat
DECK_DROP = -0.5  # The same, on a deckchair, which is lower to the ground
BUY_LINES = {
    "bait": ["Two worm packs, please.", "Any scent left in the back?", "The usual, thanks. Keep the change."],
    "food": ["One ham sandwich, and a coffee.", "Something cold, please. It is hot out.", "Got any ice cream left?"],
    "boats": ["I will want a rowing boat for the day, if you have one.", "Is the sea calm enough to row out today?"],
}
REPLY_LINES = {
    "bait": ["That is the usual. Mind the hooks.", "Fresh worms this morning, you will not be disappointed."],
    "food": ["Coming right up. Eat it on the bench.", "Coffee is fresh. Sit down and enjoy it."],
    "boats": ["Boat is ready at the pier. Bring her back by dusk.", "Calm as a pond out there. Enjoy the rowing."],
}


class Clerk:
    """A shopkeeper behind a counter. Customers are answered from here, in a bubble above the counter."""

    def __init__(self, key, name, counter, front):
        self.key = key  # The kiosk's key, which picks what they say
        self.name = name  # The kiosk's name, which their bubbles are labelled with
        self.x, self.y = counter
        self.front = front  # The tile in front of the counter, where customers stand


class Seats:
    """The seats round the place: benches and deckchairs. Someone who sits takes one, and gives it up when they stand."""

    def __init__(self, benches, deckchairs):
        self.spots = [{"x": x, "y": y, "drop": BENCH_DROP, "taken": False} for x, y in benches]
        self.spots += [{"x": x, "y": y, "drop": DECK_DROP, "taken": False} for x, y in deckchairs]


class Errands:
    """The trips: to a seat, to a counter, and the walk to get there. Anyone using it may override leave_post, after_errand
    and arrived to take their own part in a trip."""

    def init_errands(self, seats, clerks):
        self.seats = seats
        self.clerks = clerks  # The shopkeepers, by kiosk key
        self.path = []  # The tiles still to walk on the current errand
        self.errand = None  # None when at home, or "seat", "shop" or another errand on the way, "sit" or "buy" once there
        self.errand_timer = 0.0
        self.seat = None  # The seat taken for a rest
        self.shop = None  # The clerk being bought from
        self.pending = None  # A clerk's answer waiting to be said: (clerk, text, seconds to go)
        self.height = 0.0  # How far the body sits above the ground: lower when seated
        self.walk_phase = 0.0  # Swings the legs while walking

    def say(self, text, speaker=None):
        """Says a line in a bubble: their own, or a clerk's answer."""
        self.events.append((speaker or self, text))

    def face_point(self, x, y):
        """Turns to look at a point on the ground."""
        self.node.setH(math.degrees(math.atan2(-(x - self.x), y - self.y)))

    def leave_post(self):
        """Called as an errand starts. Nothing by default."""

    def after_errand(self):
        """Called when a seat or counter errand ends. Nothing by default."""

    def arrived(self, errand):
        """Called when a walk ends for an errand this module does not handle. Nothing by default."""

    def go_to(self, goal, errand):
        """Sets off along the path to a tile, on an errand. False if there is no path."""
        here = (int(self.x), int(self.y))
        self.level.blocked.discard(self.tile)  # Their own tile is free while they are away from it
        path = self.level.route(here, goal, self.level.walkable) or []
        if not path:
            self.level.blocked.add(self.tile)
            return False
        self.path = path
        self.errand = errand
        self.leave_post()
        return True

    def try_seat(self):
        """Walks to the nearest free seat in reach, to rest on it. False if there is none it can get to."""
        spots = [s for s in self.seats.spots if not s["taken"] and math.hypot(s["x"] - self.x, s["y"] - self.y) <= SEAT_RANGE]
        spots.sort(key=lambda s: math.hypot(s["x"] - self.x, s["y"] - self.y))
        for spot in spots:
            approach = self.level.stand_beside((int(spot["x"]), int(spot["y"])))
            if approach and self.go_to(approach, "seat"):
                spot["taken"] = True
                self.seat = spot
                return True
        return False

    def try_shop(self):
        """Walks to a shop counter, to buy something. False if no shop can be reached."""
        clerks = list(self.clerks.values())
        random.shuffle(clerks)
        for clerk in clerks:
            if self.go_to(clerk.front, "shop"):
                self.shop = clerk
                return True
        return False

    def sit_down(self):
        """On the seat: the body sinks to it, and the legs go forward."""
        self.x, self.y = self.seat["x"], self.seat["y"]
        self.height = self.seat["drop"]
        self.body.sit(True)
        self.errand = "sit"
        self.errand_timer = random.uniform(*SIT_TIME)

    def sit_for(self, dt):
        """Rests on the seat, then gets up and carries on."""
        self.errand_timer -= dt
        if self.errand_timer > 0:
            return
        self.height = 0.0
        self.body.sit(False)
        self.body.swing_legs(0)
        self.seat["taken"] = False
        self.seat = None
        self.errand = None
        self.after_errand()

    def begin_buying(self):
        """At the counter: they say what they want, and the clerk answers a little later."""
        self.errand = "buy"
        self.errand_timer = BUY_TIME
        self.say(random.choice(BUY_LINES[self.shop.key]))
        self.pending = (self.shop, random.choice(REPLY_LINES[self.shop.key]), CLERK_REPLY)

    def buy_for(self, dt):
        """Waits at the counter while the clerk answers, then carries on."""
        self.errand_timer -= dt
        if self.pending:
            clerk, text, wait = self.pending
            wait -= dt
            if wait <= 0:
                self.say(text, clerk)
                self.pending = None
            else:
                self.pending = (clerk, text, wait)
        if self.errand_timer <= 0:
            self.errand = None
            self.shop = None
            self.after_errand()

    def walk(self, dt):
        """Walks along the path, with the legs swinging."""
        tx, ty = self.path[0][0] + 0.5, self.path[0][1] + 0.5
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        step = WALK_PACE * dt
        if dist <= step:
            self.x, self.y = tx, ty
            self.path.pop(0)
            if not self.path:
                self.arrive()
        else:
            self.x += dx / dist * step
            self.y += dy / dist * step
        self.walk_phase += dt * 8
        self.body.swing(math.sin(self.walk_phase) * 30)
        self.node.setX(self.x)
        self.node.setY(self.y)
        self.face_point(tx, ty)  # Walking on their way, they look where they are going. Anglers turn back to the water each frame

    def arrive(self):
        """At the end of a walk: a seat to sit on, a counter to buy at, or whatever else the errand was for."""
        self.body.swing(0)
        if self.errand == "seat":
            self.sit_down()
        elif self.errand == "shop":
            self.begin_buying()
        else:
            self.arrived(self.errand)

    def run_errand(self, dt):
        """Carries on with an errand that is under way. Returns False if there is none, so the caller can do its own things."""
        if self.path:
            self.walk(dt)
        elif self.errand == "sit":
            self.sit_for(dt)
        elif self.errand == "buy":
            self.buy_for(dt)
        else:
            return False
        return True
