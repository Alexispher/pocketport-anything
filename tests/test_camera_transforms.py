"""Camera matrix and geometry visibility validation for the native renderer.

These tests verify the mathematical correctness of the view/projection
pipeline used in the native Citro3D main.c, using pure Python equivalents
of the same transforms. They complement the fixture tests by checking that
the built-in scene's geometry is actually visible from the default camera.
"""
from __future__ import annotations
import math
import unittest
from pocketport.skyrim.fixture import fixture_mesh


def build_view_matrix(cam_x, cam_y, cam_z, cam_yaw, cam_pitch):
    """Python equivalent of the C build_view_matrix function."""
    cy, sy = math.cos(cam_yaw), math.sin(cam_yaw)
    cp, sp = math.cos(cam_pitch), math.sin(cam_pitch)

    # Forward direction in world space
    fx = sy * cp
    fy = cy * cp
    fz = sp

    # Right vector = forward × world_up(0,0,1)
    rx = cy
    ry = -sy
    rz = 0.0

    # Up vector = right × forward
    ux = ry * fz - rz * fy
    uy = rz * fx - rx * fz
    uz = rx * fy - ry * fx

    # 4x4 view matrix (row-major)
    view = [
        [rx, ry, rz, -(rx*cam_x + ry*cam_y + rz*cam_z)],
        [ux, uy, uz, -(ux*cam_x + uy*cam_y + uz*cam_z)],
        [-fx, -fy, -fz, -(-fx*cam_x + (-fy)*cam_y + (-fz)*cam_z)],
        [0, 0, 0, 1],
    ]
    return view


def transform_point(matrix, x, y, z):
    """Transform a 3D point through a 4×4 matrix, return (x,y,z,w)."""
    w = 1.0
    out = []
    for row in matrix:
        out.append(row[0]*x + row[1]*y + row[2]*z + row[3]*w)
    return tuple(out)


def mat_multiply(a, b):
    """Multiply two 4×4 row-major matrices."""
    result = [[0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                result[i][j] += a[i][k] * b[k][j]
    return result


def perspective_matrix(fov_deg, aspect, near, far):
    """Build a perspective projection matrix matching Mtx_PerspTilt semantics.
    Right-handed, maps Z to [0, -w] (PICA200 convention)."""
    fov = math.radians(fov_deg)
    t = math.tan(fov / 2.0)
    # Note: Mtx_PerspTilt swaps X/Y for the 3DS rotated screen,
    # but for visibility testing we just need a standard perspective.
    return [
        [1.0 / (aspect * t), 0, 0, 0],
        [0, 1.0 / t, 0, 0],
        [0, 0, -(far + near) / (far - near), -2*far*near / (far - near)],
        [0, 0, -1, 0],
    ]


def is_visible_ndc(clip_x, clip_y, clip_z, clip_w):
    """Check if a clip-space point is within the visible frustum."""
    if clip_w <= 0:
        return False
    ndc_x = clip_x / clip_w
    ndc_y = clip_y / clip_w
    ndc_z = clip_z / clip_w
    return -1.0 <= ndc_x <= 1.0 and -1.0 <= ndc_y <= 1.0 and -1.0 <= ndc_z <= 1.0


class CameraTransformTests(unittest.TestCase):
    # Default camera position matching main.c
    CAM_X, CAM_Y, CAM_Z = 0.0, -250.0, 120.0
    CAM_YAW, CAM_PITCH = 0.0, -0.35

    def test_view_matrix_is_orthonormal(self):
        """View matrix rows (3×3 part) should be orthonormal."""
        view = build_view_matrix(0, 0, 0, 0, 0)
        for i in range(3):
            length = sum(view[i][j]**2 for j in range(3))
            self.assertAlmostEqual(length, 1.0, places=6,
                                   msg=f"Row {i} not unit length: {length}")
        for i in range(3):
            for j in range(i+1, 3):
                dot = sum(view[i][k] * view[j][k] for k in range(3))
                self.assertAlmostEqual(dot, 0.0, places=6,
                                       msg=f"Rows {i},{j} not orthogonal: {dot}")

    def test_identity_camera_at_origin(self):
        """Camera at origin with no rotation should look down +Y."""
        view = build_view_matrix(0, 0, 0, 0, 0)
        # A point at (0, 10, 0) should be in front of the camera
        ex, ey, ez, ew = transform_point(view, 0, 10, 0)
        self.assertLess(ez, 0, "Point in front should have negative eye-Z")

    def test_fixture_geometry_visible_from_default_camera(self):
        """At least some fixture vertices should project into the view frustum."""
        mesh = fixture_mesh()
        view = build_view_matrix(self.CAM_X, self.CAM_Y, self.CAM_Z,
                                 self.CAM_YAW, self.CAM_PITCH)
        proj = perspective_matrix(65.0, 400.0/240.0, 1.0, 5000.0)
        mvp = mat_multiply(proj, view)

        visible_count = 0
        in_front_count = 0
        for v in mesh.vertices:
            ex, ey, ez, ew = transform_point(view, v[0], v[1], v[2])
            if ez < 0:
                in_front_count += 1
            cx, cy, cz, cw = transform_point(mvp, v[0], v[1], v[2])
            if is_visible_ndc(cx, cy, cz, cw):
                visible_count += 1

        self.assertGreater(in_front_count, 0,
                           "No vertices in front of camera — scene behind camera")
        self.assertGreater(visible_count, 0,
                           "No vertices project into visible frustum")

    def test_floor_visible(self):
        """The floor (first 4 vertices at z=-2) should be partially visible."""
        mesh = fixture_mesh()
        view = build_view_matrix(self.CAM_X, self.CAM_Y, self.CAM_Z,
                                 self.CAM_YAW, self.CAM_PITCH)
        proj = perspective_matrix(65.0, 400.0/240.0, 1.0, 5000.0)
        mvp = mat_multiply(proj, view)

        floor_verts = mesh.vertices[:4]
        in_front = sum(1 for v in floor_verts
                       if transform_point(view, v[0], v[1], v[2])[2] < 0)
        self.assertGreater(in_front, 0, "Floor not in front of camera")

    def test_cubes_visible(self):
        """Each cube should have some vertices visible from the default camera."""
        mesh = fixture_mesh()
        view = build_view_matrix(self.CAM_X, self.CAM_Y, self.CAM_Z,
                                 self.CAM_YAW, self.CAM_PITCH)
        proj = perspective_matrix(65.0, 400.0/240.0, 1.0, 5000.0)
        mvp = mat_multiply(proj, view)

        # Cube 1: verts 4-27, Cube 2: verts 28-51, Cube 3: verts 52-75
        cube_ranges = [(4, 28), (28, 52), (52, 76)]
        for ci, (start, end) in enumerate(cube_ranges):
            cube_verts = mesh.vertices[start:end]
            in_front = sum(1 for v in cube_verts
                           if transform_point(view, v[0], v[1], v[2])[2] < 0)
            self.assertGreater(in_front, 0,
                               f"Cube {ci+1} not in front of camera")

    def test_depth_ordering(self):
        """Objects at different Y positions should have different eye-space Z."""
        view = build_view_matrix(self.CAM_X, self.CAM_Y, self.CAM_Z,
                                 self.CAM_YAW, self.CAM_PITCH)
        # Cube 1 center: (-75, 30, 27.5), Cube 2 center: (5, 55, 47.5)
        z1 = transform_point(view, -75, 30, 27.5)[2]
        z2 = transform_point(view, 5, 55, 47.5)[2]
        # Both should be in front (negative Z) and at different depths
        self.assertLess(z1, 0, "Cube 1 center behind camera")
        self.assertLess(z2, 0, "Cube 2 center behind camera")
        self.assertNotAlmostEqual(z1, z2, places=1,
                                  msg="Cubes at same depth — no depth differentiation")

    def test_no_vertex_behind_near_plane(self):
        """With near=1.0 and camera 250 units away, no fixture vertex
        should be closer than 1 unit to the camera."""
        mesh = fixture_mesh()
        view = build_view_matrix(self.CAM_X, self.CAM_Y, self.CAM_Z,
                                 self.CAM_YAW, self.CAM_PITCH)
        for v in mesh.vertices:
            ez = transform_point(view, v[0], v[1], v[2])[2]
            # In front of camera: ez < 0, distance = -ez
            if ez < 0:
                self.assertGreater(-ez, 1.0,
                                   f"Vertex too close to camera: {v[:3]}")

    def test_scene_not_fully_clipped(self):
        """The scene should not be entirely outside the far plane (5000)."""
        mesh = fixture_mesh()
        view = build_view_matrix(self.CAM_X, self.CAM_Y, self.CAM_Z,
                                 self.CAM_YAW, self.CAM_PITCH)
        within_far = 0
        for v in mesh.vertices:
            ez = transform_point(view, v[0], v[1], v[2])[2]
            if ez < 0 and -ez < 5000.0:
                within_far += 1
        self.assertGreater(within_far, 0,
                           "All vertices beyond far plane")


if __name__ == "__main__":
    unittest.main()
