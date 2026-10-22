import math

from panda3d.core import Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat, GeomVertexWriter, NodePath, TransparencyAttrib, Vec3


class MeshBuilder:
    """Collects quads, triangles, boxes and ellipsoids into one lit, vertex-coloured mesh, so a whole model is one draw call.
    Colours are (r, g, b) or (r, g, b, a) from 0 to 255."""

    def __init__(self):
        self.data = GeomVertexData("mesh", GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
        self.vertex = GeomVertexWriter(self.data, "vertex")
        self.normal = GeomVertexWriter(self.data, "normal")
        self.color = GeomVertexWriter(self.data, "color")
        self.tris = GeomTriangles(Geom.UHStatic)
        self.count = 0

    def quad(self, corners, normal, color):
        """Four corners in order around the face. The winding is fixed here so the face points along normal.
        Pass the same corner twice to make a triangle. color is one colour for the whole face, or four, one for each corner,
        so a face can fade from one colour to another."""
        ab = Vec3(*corners[1]) - Vec3(*corners[0])
        ac = Vec3(*corners[2]) - Vec3(*corners[0])
        colours = list(color) if isinstance(color[0], tuple) else [color] * 4
        if ab.cross(ac).dot(Vec3(*normal)) < 0:
            corners = corners[::-1]
            colours = colours[::-1]
        for point, colour in zip(corners, colours):
            rgba = [channel / 255 for channel in colour] + ([1.0] if len(colour) == 3 else [])
            self.vertex.addData3(*point)
            self.normal.addData3(*normal)
            self.color.addData4(*rgba)
        i = self.count
        self.tris.addVertices(i, i + 1, i + 2)
        self.tris.addVertices(i, i + 2, i + 3)
        self.count += 4

    def triangle(self, a, b, c, color):
        normal = Vec3(*b) - Vec3(*a)
        normal = normal.cross(Vec3(*c) - Vec3(*a))
        normal.normalize()
        self.quad([a, b, c, c], (normal.x, normal.y, normal.z), color)

    def triangle_both(self, a, b, c, color):
        """A triangle drawn from both sides, so a sail or a bow shows from either side of the boat."""
        self.triangle(a, b, c, color)
        self.triangle(a, c, b, color)

    def box(self, x, y, z, w, d, h, color):
        """An axis-aligned box with its corner at (x, y, z), w across, d deep and h tall."""
        x1, y1, z1 = x + w, y + d, z + h
        faces = [
            ((0, 0, 1), [(x, y, z1), (x1, y, z1), (x1, y1, z1), (x, y1, z1)]),
            ((0, 0, -1), [(x, y, z), (x, y1, z), (x1, y1, z), (x1, y, z)]),
            ((0, -1, 0), [(x, y, z), (x1, y, z), (x1, y, z1), (x, y, z1)]),
            ((0, 1, 0), [(x, y1, z), (x, y1, z1), (x1, y1, z1), (x1, y1, z)]),
            ((-1, 0, 0), [(x, y, z), (x, y, z1), (x, y1, z1), (x, y1, z)]),
            ((1, 0, 0), [(x1, y, z), (x1, y1, z), (x1, y1, z1), (x1, y, z1)]),
        ]
        for normal, corners in faces:
            self.quad(corners, normal, color)

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, color, steps=8):
        """A smooth ellipsoid, built as latitude and longitude bands."""
        def point(u, v):
            theta, phi = math.pi * u, 2 * math.pi * v
            return (cx + rx * math.sin(theta) * math.cos(phi), cy + ry * math.sin(theta) * math.sin(phi), cz + rz * math.cos(theta))

        def normal_at(p):
            nx, ny, nz = (p[0] - cx) / rx ** 2, (p[1] - cy) / ry ** 2, (p[2] - cz) / rz ** 2
            length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
            return (nx / length, ny / length, nz / length)

        for i in range(steps):
            for j in range(steps * 2):
                corners = [point(i / steps, j / (steps * 2)), point((i + 1) / steps, j / (steps * 2)),
                           point((i + 1) / steps, (j + 1) / (steps * 2)), point(i / steps, (j + 1) / (steps * 2))]
                mid = [sum(c[k] for c in corners) / 4 for k in range(3)]
                self.quad(corners, normal_at(mid), color)

    def build(self, name, transparent=False):
        geom = Geom(self.data)
        geom.addPrimitive(self.tris)
        node = GeomNode(name)
        node.addGeom(geom)
        path = NodePath(node)
        if transparent:
            path.setTransparency(TransparencyAttrib.MAlpha)
        return path
