"""People: the angler, the NPC anglers, the shopkeepers and the walkers. Each is built from boxes, with legs that swing as
they walk, arms and hands that reach for a rod or a counter, and a face whose expression shows what they are doing.
A person faces +y."""
import math

from iso.mesh import MeshBuilder

SKIN = (214, 170, 132)
TROUSERS = (42, 38, 44)
SHOE = (46, 36, 32)
BELT = (58, 42, 30)
BAND = (176, 146, 78)  # The band round a hat, in gold
ROD = (96, 74, 48)
INK = (30, 30, 36)
LEG_LENGTH = 0.7
HIP_X = 0.12  # Legs sit either side of the middle, this far out
SHOULDER = (0.3, 0.0, 1.22)  # Shoulder pivots, either side of the torso
ARM_LENGTH = 0.62
HEAD = (0.0, 0.0, 1.42)  # The head's centre
FACE_Y = 0.15  # The face is on the front of the head, this far in front of its centre

# Arm poses, as the pitch of each arm pivot in degrees. Positive pitch swings the arm forward.
ROD_ARM = 75  # The right hand holds the rod out in front, the left hand steadies it
ROD_LEFT = 55
COUNTER_ARM = 80  # Both hands rest on a counter
SEAT_LEGS = 85  # Thighs forward, when sitting on a boat's seat
ROW_ARM = 35  # The arms reach forward at this pitch while rowing, and swing back and forth about it
ROW_REACH = 28
CARRY_ROD = (0.0, -0.3, 0.92)  # Where the rod's butt sits when it is carried on the back: behind the torso and clear of the hat's back edge at y -0.2
CARRY_HPR = (0, 90, 0)  # Pitched up, so the rod stands vertical with its tip above the head


class Body:
    """A person's parts. Legs, arms and head are pivots, so they can be posed and swung."""

    def __init__(self, node, legs, arms, head, rod):
        self.node = node
        self.legs = legs  # Left, then right
        self.arms = arms  # Left, then right
        self.head = head
        self.rod = rod  # The rod, if the person holds one, hung from the right hand
        self.rod_out = True  # False while the rod is carried on the back
        self.face = None
        self.expression = None

    def set_rod_out(self, out):
        """Holds the rod out in front, in the right hand, or carries it on the back. Only reparents when it changes."""
        if self.rod is None or out == self.rod_out:
            return
        self.rod_out = out
        if out:
            self.rod.reparentTo(self.arms[1])
            self.rod.setPos(0, 0, -ARM_LENGTH - 0.05)
            self.rod.setHpr(0, 35 - ROD_ARM, 0)
        else:
            self.rod.reparentTo(self.node)
            self.rod.setPos(*CARRY_ROD)
            self.rod.setHpr(*CARRY_HPR)

    def sit(self, on):
        """Sits on a seat: the thighs stretch forward. Standing again hands the legs back to the walk."""
        if on:
            self.legs[0].setP(SEAT_LEGS)
            self.legs[1].setP(SEAT_LEGS)

    def row(self, stride):
        """The arms work the oars: forward and back, in step with the stroke."""
        reach = ROW_ARM + ROW_REACH * math.sin(stride)
        self.arms[0].setP(reach)
        self.arms[1].setP(reach)

    def swing_legs(self, amount):
        """The legs swing as the person walks. amount is the swing in degrees."""
        self.legs[0].setP(amount)
        self.legs[1].setP(-amount)

    def swing(self, amount):
        """The walk cycle for someone with their arms free: the arms swing against the legs."""
        self.swing_legs(amount)
        self.arms[0].setP(-amount * 0.6)
        self.arms[1].setP(amount * 0.6)

    def pose(self, name):
        """Puts the arms in a pose: rod, counter, or rest, where they hang at the sides."""
        if name == "rod":
            self.arms[1].setP(ROD_ARM)
            self.arms[0].setP(ROD_LEFT)
        elif name == "counter":
            self.arms[0].setP(COUNTER_ARM)
            self.arms[1].setP(COUNTER_ARM)
        else:
            self.arms[0].setP(0)
            self.arms[1].setP(0)

    def set_expression(self, name):
        """Rebuilds the face for an expression, if it has changed. Names are in FACES."""
        if name == self.expression:
            return
        self.expression = name
        if self.face:
            self.face.removeNode()
        mesh = MeshBuilder()
        eyes, mouth = FACES.get(name, FACES["neutral"])
        for x in (-0.055, 0.055):
            eye_w, eye_h = eyes
            mesh.box(x - eye_w / 2, FACE_Y - 0.01, 0.03 - eye_h / 2, eye_w, 0.02, eye_h, INK)
        for box in mouth:
            mesh.box(*box, INK)
        self.face = mesh.build("face")
        self.face.reparentTo(self.head)


# Each face: the eyes as (width, height), and the mouth as boxes (x, y, z, w, d, h) relative to the head's centre
FACES = {
    "neutral": ((0.03, 0.04), [(-0.04, FACE_Y - 0.005, -0.06, 0.08, 0.01, 0.012)]),
    "smile": ((0.03, 0.04), [(-0.05, FACE_Y - 0.005, -0.06, 0.10, 0.01, 0.012),
                             (-0.065, FACE_Y - 0.005, -0.045, 0.02, 0.01, 0.02), (0.045, FACE_Y - 0.005, -0.045, 0.02, 0.01, 0.02)]),
    "happy": ((0.035, 0.012), [(-0.05, FACE_Y - 0.005, -0.06, 0.10, 0.01, 0.012),
                               (-0.065, FACE_Y - 0.005, -0.045, 0.02, 0.01, 0.02), (0.045, FACE_Y - 0.005, -0.045, 0.02, 0.01, 0.02)]),
    "focus": ((0.035, 0.014), [(-0.03, FACE_Y - 0.005, -0.06, 0.06, 0.01, 0.012)]),
    "talk": ((0.03, 0.04), [(-0.03, FACE_Y - 0.005, -0.09, 0.06, 0.01, 0.05)]),
    "surprised": ((0.05, 0.05), [(-0.025, FACE_Y - 0.005, -0.095, 0.05, 0.01, 0.05)]),
    "strain": ((0.035, 0.014), [(-0.03, FACE_Y - 0.005, -0.07, 0.06, 0.01, 0.012)]),
    "sad": ((0.03, 0.04), [(-0.04, FACE_Y - 0.005, -0.08, 0.08, 0.01, 0.012),
                           (-0.06, FACE_Y - 0.005, -0.06, 0.02, 0.01, 0.02), (0.04, FACE_Y - 0.005, -0.06, 0.02, 0.01, 0.02)]),
}


def build_body(parent, name, coat, hat, trousers=TROUSERS, rod=False, hair=None, skirt=False):
    """Builds a person under parent. hat is the colour of their hat, or None for no hat, and rod gives them a rod in their right hand.
    hair is the colour of their hair, for long hair, and skirt hangs a skirt in the coat's colour from the waist."""
    node = parent.attachNewNode(name)
    legs = []
    for side in (-1, 1):
        mesh = MeshBuilder()
        mesh.box(-0.07, -0.08, -LEG_LENGTH, 0.14, 0.16, LEG_LENGTH, trousers)
        mesh.box(-0.075, -0.09, -LEG_LENGTH, 0.15, 0.25, 0.1, SHOE)  # A shoe, with the toe pointing forward
        leg = mesh.build("leg")
        leg.reparentTo(node)
        leg.setPos(HIP_X * side, 0, LEG_LENGTH)  # Legs pivot at the hip
        legs.append(leg)

    mesh = MeshBuilder()
    mesh.box(-0.24, -0.16, 0.7, 0.48, 0.32, 0.62, coat)
    mesh.box(-0.245, -0.165, 0.7, 0.49, 0.33, 0.08, BELT)  # A belt round the waist
    mesh.build("torso").reparentTo(node)
    if skirt:
        mesh = MeshBuilder()
        mesh.box(-0.27, -0.2, 0.3, 0.54, 0.4, 0.42, coat)  # Hangs from the waist over the top of the legs, which swing under it
        mesh.build("skirt").reparentTo(node)

    head = node.attachNewNode("head")
    head.setPos(*HEAD)
    mesh = MeshBuilder()
    mesh.ellipsoid(0, 0, 0, 0.15, 0.15, 0.15, SKIN, steps=5)
    if hat is not None:
        mesh.box(-0.2, -0.2, 0.08, 0.4, 0.4, 0.05, hat)
        mesh.box(-0.205, -0.205, 0.08, 0.41, 0.41, 0.02, BAND)
        mesh.box(-0.13, -0.13, 0.13, 0.26, 0.26, 0.14, hat)
    if hair is not None:
        mesh.box(-0.17, -0.17, 0.1, 0.34, 0.34, 0.06, hair)  # Hair over the crown
        mesh.box(-0.17, -0.2, -0.22, 0.34, 0.1, 0.34, hair)  # Hair falling down behind the head
    mesh.build("head").reparentTo(head)

    arms = []
    for side in (-1, 1):
        pivot = node.attachNewNode("arm")
        pivot.setPos(SHOULDER[0] * side, SHOULDER[1], SHOULDER[2])
        mesh = MeshBuilder()
        mesh.box(-0.07, -0.07, -ARM_LENGTH, 0.14, 0.14, ARM_LENGTH, coat)
        mesh.box(-0.078, -0.078, -ARM_LENGTH, 0.156, 0.156, 0.04, tuple(int(c * 0.7) for c in coat))  # A cuff at the wrist
        mesh.ellipsoid(0, 0, -ARM_LENGTH - 0.05, 0.08, 0.08, 0.08, SKIN, steps=4)  # The hand
        mesh.build("arm_part").reparentTo(pivot)
        arms.append(pivot)

    rod_node = None
    if rod:
        # The rod hangs from the right hand, tilted up. Its arm pivot is posed forward, so the rod's own tilt is relative to it
        mesh = MeshBuilder()
        mesh.box(-0.02, 0, 0, 0.04, 1.2, 0.04, ROD)
        rod_node = mesh.build("rod")
        rod_node.reparentTo(arms[1])
        rod_node.setPos(0, 0, -ARM_LENGTH - 0.05)
        rod_node.setP(35 - ROD_ARM)
    return Body(node, legs, arms, head, rod_node)
