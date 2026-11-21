"""Three-dimensional view of one design, drawn from the same geometry rules as the EnergyPlus models.

Coordinates follow the IDF templates: x runs along the front (south) facade, y runs from the front to
the back (north) facade, and the gable roof rises 2 m above the eaves with its ridge at y = L / 2. The
building is then rotated clockwise by the sampled orientation (the EnergyPlus North Axis), so true north
always points up the screen.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import plotly.graph_objects as go

from common import ROOT

sys.path.append(str(ROOT))
from src.geometry import (  # noqa: E402
    EDGE_MARGIN,
    HEAD_CLEARANCE,
    MAX_HEAD_HEIGHT,
    SILL_HEIGHT,
    door_band,
    three_window_band,
)

DOOR_X = (4.475, 5.475)
DOOR_HEIGHT = 2.25
RIDGE_RISE = 2.0
OVERHANG_ABOVE_HEAD = 0.5
OVERHANG_EXTENSION = 0.5
OVERHANG_THICKNESS = 0.06
GLASS_OFFSET = 0.03

WALL = "#ECE7DF"
EDGE = "#55595F"
GLASS_CLEAR = np.array([156, 205, 232])
GLASS_TINTED = np.array([46, 88, 120])
ROOF_LIGHT = np.array([205, 208, 212])
ROOF_DARK = np.array([58, 62, 68])
OVERHANG = "#4C5259"
DOOR = "#7A5C46"
NEIGHBOUR = "#C9CDD2"
GROUND = "#EEF1EA"


def _mix(light: np.ndarray, dark: np.ndarray, t: float) -> str:
    r, g, b = (light + (dark - light) * min(max(t, 0.0), 1.0)).round().astype(int)
    return f"rgb({r},{g},{b})"


def _windows(design: dict, archetype: str) -> tuple[list[tuple], float]:
    """Window rectangles as (facade, storey, a1, a2, z1, z2) and the realised glazed area.

    ``a`` is the position along the facade: x for the front and back, y for the sides.
    """
    W, L, H, wwr = design["width"], design["length"], design["height"], design["wwr"]
    z1, z2 = SILL_HEIGHT, min(MAX_HEAD_HEIGHT, H - HEAD_CLEARANCE)
    window_height = z2 - z1
    windows, area = [], 0.0

    def band(facade: str, storey: int, xs: tuple, band_area: float) -> None:
        nonlocal area
        area += band_area
        for a1, a2 in (xs[0:2], xs[2:4], xs[4:6]):
            if a2 - a1 > 1e-6:
                windows.append((facade, storey, a1, a2, z1, z2))

    for storey in (0, 1):
        band("north", storey, *three_window_band(W, wwr, H, window_height))
    band("south", 1, *three_window_band(W, wwr, H, window_height))
    band("south", 0, *door_band(W, wwr, H, window_height))

    side = min(wwr * L * H / window_height, max(0.0, L - 1.0))
    y1, y2 = max(EDGE_MARGIN, L / 2 - side / 2), min(L - EDGE_MARGIN, L / 2 + side / 2)
    sides = ["west"] if archetype == "semi" else ["west", "east"]
    for facade in sides:
        for storey in (0, 1):
            if y2 - y1 > 1e-6:
                windows.append((facade, storey, y1, y2, z1, z2))
                area += (y2 - y1) * window_height
    return windows, area


def realised_wwr(design: dict, archetype: str) -> float:
    """Glazed area over the area of the facades that carry windows."""
    W, L, H = design["width"], design["length"], design["height"]
    _, area = _windows(design, archetype)
    walls = 2 * (2 * W * H) + (1 if archetype == "semi" else 2) * 2 * L * H
    return area / walls


class _Scene:
    def __init__(self, design: dict) -> None:
        self.W, self.L = design["width"], design["length"]
        angle = math.radians(design["orientation"])
        self.cos, self.sin = math.cos(angle), math.sin(angle)
        self.meshes: dict[tuple[str, float], list] = {}
        self.edges: dict[tuple[str, float, str], list] = {}

    def world(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """Centre the plan on the origin and rotate clockwise by the North Axis."""
        x, y = x - self.W / 2, y - self.L / 2
        return x * self.cos + y * self.sin, -x * self.sin + y * self.cos, z

    def polygon(self, points, colour: str, opacity: float = 1.0, edge: str | None = EDGE, width: float = 2.0) -> None:
        vertices, faces = self.meshes.setdefault((colour, opacity), [[], []])
        start = len(vertices)
        vertices.extend(self.world(*p) for p in points)
        faces.extend((start, start + i, start + i + 1) for i in range(1, len(points) - 1))
        if edge:
            line = self.edges.setdefault((edge, width, "solid"), [])
            line.extend([self.world(*p) for p in [*points, points[0]]] + [(None, None, None)])

    def box(self, x0, x1, y0, y1, z0, z1, colour: str, opacity: float = 1.0, edge: str | None = EDGE) -> None:
        corners = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
        top = [(x, y, z1) for x, y, _ in corners]
        self.polygon(corners, colour, opacity, edge, 1.0)
        self.polygon(top, colour, opacity, edge, 1.0)
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            self.polygon([a, b, (b[0], b[1], z1), (a[0], a[1], z1)], colour, opacity, edge, 1.0)

    def traces(self) -> list:
        traces = []
        for (colour, opacity), (vertices, faces) in self.meshes.items():
            v, f = np.array(vertices), np.array(faces)
            traces.append(
                go.Mesh3d(
                    x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                    color=colour, opacity=opacity, flatshading=True, hoverinfo="skip",
                    lighting=dict(ambient=0.72, diffuse=0.55, specular=0.05, roughness=0.9),
                    lightposition=dict(x=-5e4, y=-1e5, z=1e5),
                )
            )  # fmt: skip
        for (colour, width, dash), points in self.edges.items():
            p = np.array(points, dtype=float)
            traces.append(
                go.Scatter3d(
                    x=p[:, 0], y=p[:, 1], z=p[:, 2], mode="lines", hoverinfo="skip",
                    line=dict(color=colour, width=width, dash=dash),
                )
            )  # fmt: skip
        return traces


def _shell(scene: _Scene, W: float, L: float, H: float, x_shift: float, colour: str, opacity: float, edge) -> None:
    """Walls, gables and roof of a two-storey gabled box occupying x_shift .. x_shift + W."""
    a, b, top, ridge = x_shift, x_shift + W, 2 * H, 2 * H + RIDGE_RISE
    scene.polygon([(a, 0, 0), (b, 0, 0), (b, 0, top), (a, 0, top)], colour, opacity, edge)
    scene.polygon([(b, L, 0), (a, L, 0), (a, L, top), (b, L, top)], colour, opacity, edge)
    for x in (a, b):
        scene.polygon([(x, 0, 0), (x, L, 0), (x, L, top), (x, L / 2, ridge), (x, 0, top)], colour, opacity, edge)


def figure(design: dict, archetype: str, pinned: dict | None = None) -> go.Figure:
    W, L, H = design["width"], design["length"], design["height"]
    scene = _Scene(design)

    # Ground, with a ring of compass labels added in true-north coordinates below.
    radius = max(W, L) * 1.05 + (W if archetype == "semi" else 0) * 0.5
    angles = np.linspace(0, 2 * np.pi, 49)
    ground = [(radius * math.cos(t), radius * math.sin(t), -0.02) for t in angles[:-1]]
    vertices, faces = scene.meshes.setdefault((GROUND, 1.0), [[], []])
    centre = len(vertices)
    vertices.append((0.0, 0.0, -0.02))
    vertices.extend(ground)
    faces.extend((centre, centre + 1 + i, centre + 1 + (i + 1) % 48) for i in range(48))

    if archetype == "semi":
        _shell(scene, W, L, H, W, NEIGHBOUR, 0.35, "#A3A8AE")
        eave, top = 2 * H, 2 * H + RIDGE_RISE
        for y in (0, L):
            slope = [(W, y, eave), (2 * W, y, eave), (2 * W, L / 2, top), (W, L / 2, top)]
            scene.polygon(slope, NEIGHBOUR, 0.35, "#A3A8AE")

    _shell(scene, W, L, H, 0.0, WALL, 1.0, EDGE)
    roof = _mix(ROOF_LIGHT, ROOF_DARK, (design["roofAbsorptance"] - 0.3) / 0.6)
    ridge = 2 * H + RIDGE_RISE
    scene.polygon([(0, 0, 2 * H), (W, 0, 2 * H), (W, L / 2, ridge), (0, L / 2, ridge)], roof)
    scene.polygon([(W, L, 2 * H), (0, L, 2 * H), (0, L / 2, ridge), (W, L / 2, ridge)], roof)
    # Floor line between storeys on every exposed facade.
    floor_line = scene.edges.setdefault(("#9AA0A6", 1.5, "solid"), [])
    corners = [(0, 0), (W, 0), (W, L), (0, L), (0, 0)]
    floor_line.extend([scene.world(x, y, H) for x, y in corners] + [(None,) * 3])

    glass = _mix(GLASS_CLEAR, GLASS_TINTED, (0.7 - design["g_value"]) / 0.5)
    depth = design["fixedShadingDepth"]
    o = GLASS_OFFSET
    windows, _ = _windows(design, archetype)
    for facade, storey, a1, a2, z1, z2 in windows:
        z1, z2 = z1 + storey * H, z2 + storey * H
        zo = z2 + OVERHANG_ABOVE_HEAD
        e = OVERHANG_EXTENSION
        if facade == "south":
            scene.polygon([(a1, -o, z1), (a2, -o, z1), (a2, -o, z2), (a1, -o, z2)], glass, 0.95)
            if depth > 0:
                scene.box(a1 - e, a2 + e, -depth, 0, zo, zo + OVERHANG_THICKNESS, OVERHANG)
        elif facade == "north":
            scene.polygon([(a2, L + o, z1), (a1, L + o, z1), (a1, L + o, z2), (a2, L + o, z2)], glass, 0.95)
            if depth > 0:
                scene.box(a1 - e, a2 + e, L, L + depth, zo, zo + OVERHANG_THICKNESS, OVERHANG)
        elif facade == "west":
            scene.polygon([(-o, a2, z1), (-o, a1, z1), (-o, a1, z2), (-o, a2, z2)], glass, 0.95)
            if depth > 0:
                scene.box(-depth, 0, a1 - e, a2 + e, zo, zo + OVERHANG_THICKNESS, OVERHANG)
        else:
            scene.polygon([(W + o, a1, z1), (W + o, a2, z1), (W + o, a2, z2), (W + o, a1, z2)], glass, 0.95)
            if depth > 0:
                scene.box(W, W + depth, a1 - e, a2 + e, zo, zo + OVERHANG_THICKNESS, OVERHANG)
    if W >= DOOR_X[1] + EDGE_MARGIN:
        (d1, d2), dh = DOOR_X, DOOR_HEIGHT
        scene.polygon([(d1, -o, 0), (d2, -o, 0), (d2, -o, dh), (d1, -o, dh)], DOOR)

    traces = scene.traces()

    if pinned is not None:
        ghost = _Scene(pinned)
        Wp, Lp, Hp = pinned["width"], pinned["length"], pinned["height"]
        rp = 2 * Hp + RIDGE_RISE
        outline = ghost.edges.setdefault(("#D1495B", 3.0, "dash"), [])
        for z in (0, 2 * Hp):
            outline.extend(
                [ghost.world(x, y, z) for x, y in [(0, 0), (Wp, 0), (Wp, Lp), (0, Lp), (0, 0)]] + [(None,) * 3]
            )
        for x in (0, Wp):
            outline.extend(
                [ghost.world(x, 0, 2 * Hp), ghost.world(x, Lp / 2, rp), ghost.world(x, Lp, 2 * Hp), (None,) * 3]
            )
        for x, y in [(0, 0), (Wp, 0), (Wp, Lp), (0, Lp)]:
            outline.extend([ghost.world(x, y, 0), ghost.world(x, y, 2 * Hp), (None,) * 3])
        outline.extend([ghost.world(0, Lp / 2, rp), ghost.world(Wp, Lp / 2, rp), (None,) * 3])
        traces += ghost.traces()

    labels = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
    traces.append(
        go.Scatter3d(
            x=[radius * 0.93 * dx for dx, _ in labels.values()],
            y=[radius * 0.93 * dy for _, dy in labels.values()],
            z=[0.05] * 4,
            mode="text",
            text=[f"<b>{k}</b>" if k == "N" else k for k in labels],
            textfont=dict(size=14, color=["#D1495B", "#55595F", "#55595F", "#55595F"]),
            hoverinfo="skip",
        )
    )

    extent = radius * 1.02
    axis = dict(visible=False, showbackground=False)
    fig = go.Figure(traces)
    fig.update_layout(
        showlegend=False,
        height=430,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        uirevision="house",
        scene=dict(
            xaxis=dict(axis, range=[-extent, extent]),
            yaxis=dict(axis, range=[-extent, extent]),
            zaxis=dict(axis, range=[-0.1, extent]),
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=0.5),
            camera=dict(eye=dict(x=-0.88, y=-1.12, z=0.55), center=dict(x=0, y=0, z=-0.22)),
            dragmode="turntable",
        ),
    )
    return fig
