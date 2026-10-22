import math

from iso.people import build_body

SPEED = 4.5  # Tiles per second on foot
SEAT_Z = -0.55  # Height of the angler's body when sitting in a boat, so the hips sit on the seat
BENCH_Z = -0.22  # Height of the body when sitting on a bench, whose seat is 0.48 up, so the hips sit on it
ROD = (96, 74, 48)


class Angler:
    def __init__(self, render, tile):
        self.x, self.y = tile[0] + 0.5, tile[1] + 0.5  # Stands in the middle of its tile
        self.path = []  # Points still to walk to, as (x, y) tile centres
        self.stride = 0.0  # Walk cycle, which swings the legs while moving
        self.driven = False  # Set when the keys walk the angler, so the walk cycle runs
        self.rod_out = False  # The rod is held out in front only when fishing and standing still. Otherwise it is carried on the back
        self.sitting = False  # Sitting in a rowing boat, on the water
        self.seated = False  # Resting on a bench
        self.waiting = False  # Stopped on the path, because someone is on the next tile
        self.node = render.attachNewNode("angler")
        self.outfit = {"coat": (72, 60, 46), "hat": (34, 30, 28), "trousers": (96, 84, 60)}  # Colours of the clothes being worn
        self.build()
        self.place()

    def dress(self, outfit):
        """Rebuilds the angler in the clothes given, a dict of colours for the coat, hat and trousers."""
        self.outfit = outfit
        self.body.node.removeNode()
        self.build()
        self.place()

    def build(self):
        self.body = build_body(self.node, "angler", self.outfit["coat"], self.outfit["hat"], self.outfit["trousers"], rod=True)
        self.legs = self.body.legs
        self.rod = self.body.rod
        # The tip of the rod, at the top of the rod's 1.2 length. The line leaves from here.
        self.tip = self.rod.attachNewNode("rod_tip")
        self.tip.setPos(0, 1.2, 0)

    def rod_tip(self, render):
        """Where the line leaves the rod, in the world."""
        return self.tip.getPos(render)

    def tile(self):
        return int(self.x), int(self.y)

    def walk_to(self, tiles):
        self.seated = False
        self.path = [(x + 0.5, y + 0.5) for x, y in tiles]

    def sit_down(self, x, y):
        """Sits on a bench at this point, to rest. Walking off, or standing up, ends the rest."""
        self.path = []
        self.seated = True
        self.x, self.y = x, y
        self.place()

    def stand(self):
        self.seated = False

    def stop(self):
        self.path = []

    def moving(self):
        return (bool(self.path) and not self.waiting) or self.driven

    def step_to(self, x, y, dx, dy):
        """Moves the angler straight to (x, y) when the keys walk it, facing the way it moves."""
        self.path = []
        self.seated = False
        self.x, self.y = x, y
        self.face(dx, dy)
        self.driven = True
        self.place()

    def update(self, dt, blocked=None):
        """Walks along the path. Returns True on the frame the angler reaches the end of it. blocked(x, y) says whether a
        tile is taken by someone else: the angler waits until it is clear, rather than walking through them."""
        arrived = False
        self.waiting = bool(self.path) and bool(blocked) and blocked(int(self.path[0][0]), int(self.path[0][1]))
        if self.path and not self.waiting:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            step = SPEED * dt
            if dist <= step:
                self.x, self.y = tx, ty
                self.path.pop(0)
                arrived = not self.path
            else:
                self.x += dx / dist * step
                self.y += dy / dist * step
                self.face(dx, dy)
        if self.moving() or self.driven:
            self.stride = (self.stride + dt * 11) % (2 * math.pi)
        else:
            self.stride *= max(0.0, 1 - dt * 8)  # Settles back to standing still
        self.driven = False  # Set again by the keys each frame that they are held
        self.place()
        return arrived

    def face(self, dx, dy):
        self.node.setH(math.degrees(math.atan2(-dx, dy)))

    def look_at(self, x, y):
        self.face(x - self.x, y - self.y)

    def place(self):
        """Poses the angler: sitting and rowing in a boat, fishing with the rod out, or walking with the rod on the back."""
        self.node.setPos(self.x, self.y, 0)
        self.body.set_rod_out(self.rod_out)
        if self.seated:
            self.body.sit(True)
            self.node.setZ(BENCH_Z)
            self.body.pose("rest")
            return
        swing = math.sin(self.stride) * 35
        if self.sitting:
            self.body.sit(True)
            self.node.setZ(SEAT_Z)
            if self.moving():
                self.body.row(self.stride)  # Rowing
            elif self.rod_out:
                self.body.pose("rod")
            else:
                self.body.pose("rest")
            return
        self.body.sit(False)
        if self.rod_out:
            self.body.swing_legs(swing)
            self.body.pose("rod")
        else:
            self.body.swing(swing)
        self.node.setZ(abs(math.sin(self.stride)) * 0.05)
