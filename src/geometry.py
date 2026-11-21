"""Parametric geometry: turn one sampled design into IDF placeholder values.

The house is a two-storey box, W wide (north and south facades) and L deep (east and
west facades), with storey height H. Every window sits in one horizontal band between a
0.8 m sill and a head at min(2.2 m, H - 0.3 m). On each facade the sampled window-to-wall
ratio (WWR) sets the total glazed width of that band:

* north and first-floor south: three equal windows separated by 0.3 m mullions;
* ground-floor south: one window either side of the front door;
* east and west: one centred window.

Glazing is clipped where it cannot fit between the edge margins, mullions and door, so
the realised WWR can be lower than the sampled value. Openable area is the window
opening factor (WOF) times the realised glazed area.
"""

from __future__ import annotations

import math

SILL_HEIGHT = 0.8  # m
MAX_HEAD_HEIGHT = 2.2  # m
HEAD_CLEARANCE = 0.3  # m between window head and ceiling
EDGE_MARGIN = 0.5  # m between facade edge and glazing
MULLION_GAP = 0.3  # m between adjacent windows
DOOR_START_X = 4.475  # m, ground-floor south door
DOOR_END_X = 5.475  # m

HEATING_SETPOINT = 21.0  # deg C
COOLING_SETPOINT = 100.0  # deg C; never reached, so summer is free-running
VENTILATION_RATE = 0.0
INTERNAL_MASS = 20.0

Band = tuple[float, float, float, float, float, float]


def three_window_band(facade_width: float, wwr: float, height: float, window_height: float) -> tuple[Band, float]:
    """x-coordinates (start/end of three windows) and glazed area of a three-window band."""
    target_width = wwr * facade_width * height / window_height
    available = max(0.0, facade_width - 2 * EDGE_MARGIN - 2 * MULLION_GAP)
    total_width = min(target_width, available)
    single = total_width / 3.0
    x1 = EDGE_MARGIN
    x2 = x1 + single
    x3 = x2 + MULLION_GAP
    x4 = x3 + single
    x5 = x4 + MULLION_GAP
    x6 = x5 + single
    return (x1, x2, x3, x4, x5, x6), total_width * window_height


def door_band(facade_width: float, wwr: float, height: float, window_height: float) -> tuple[Band, float]:
    """x-coordinates and glazed area of the ground-floor south band, split around the door.

    Glazing is shared between the two sides in proportion to the space each side offers.
    """
    target_width = wwr * facade_width * height / window_height
    left_available = max(0.0, DOOR_START_X - EDGE_MARGIN)
    right_available = max(0.0, facade_width - EDGE_MARGIN - DOOR_END_X)
    available = left_available + right_available
    total_width = min(target_width, available)
    if available > 0:
        left = total_width * left_available / available
        right = total_width * right_available / available
    else:
        left = right = 0.0
    x1 = EDGE_MARGIN
    x2 = x1 + left
    x5 = max(DOOR_END_X, facade_width - EDGE_MARGIN - right)
    x6 = facade_width - EDGE_MARGIN
    return (x1, x2, DOOR_START_X, DOOR_START_X, x5, x6), (left + right) * window_height


def sap_occupancy(floor_area: float) -> float:
    """Assumed number of occupants for a dwelling of this total floor area (SAP 2012)."""
    excess = floor_area - 13.9
    return 1 + 1.76 * (1 - math.exp(-0.000349 * excess**2)) + 0.0013 * excess


def placeholder_values(design: dict) -> dict[str, str]:
    """Map every ``@placeholder@`` in config/templates/*.idf to its value for one design."""
    W, L, H = design["width"], design["length"], design["height"]
    wwr, wof = design["wwr"], design["wof"]

    z1 = SILL_HEIGHT
    z2 = min(MAX_HEAD_HEIGHT, H - HEAD_CLEARANCE)
    window_height = z2 - z1

    north, area_north = three_window_band(W, wwr, H, window_height)
    south_upper, area_south_upper = three_window_band(W, wwr, H, window_height)
    south_ground, area_south_ground = door_band(W, wwr, H, window_height)

    # East and west: one centred window per facade.
    side_width = min(wwr * L * H / window_height, max(0.0, L - 1.0))
    centre = L / 2.0
    side_y1 = max(0.5, centre - side_width / 2.0)
    side_y2 = min(L - 0.5, centre + side_width / 2.0)
    area_side = max(0.0, side_y2 - side_y1) * window_height

    # Two equal occupied zones share the household and the whole-dwelling leakage.
    people_per_zone = sap_occupancy(2 * W * L) / 2.0
    flow_per_zone = design["flowCoefficient"] / 2.0

    values = {
        "@width@": f"{W}",
        "@length@": f"{L}",
        "@height@": f"{H}",
        "@orientation@": f"{design['orientation']}",
        "@wallInsulationThickness@": f"{design['wallInsulationThickness']}",
        "@roofInsulationThickness@": f"{design['roofInsulationThickness']}",
        "@slabInsulationThickness@": f"{design['slabInsulationThickness']}",
        "@u_windows@": f"{design['u_windows']}",
        "@g_value@": f"{design['g_value']}",
        "@roofAbsorptance@": f"{design['roofAbsorptance']}",
        "@flowCoefficient_101@": f"{flow_per_zone:.8f}",
        "@flowCoefficient_102@": f"{flow_per_zone:.8f}",
        "@fixedShadingDepth@": f"{design['fixedShadingDepth']}",
        "@heatingSetpoint@": f"{HEATING_SETPOINT}",
        "@coolingSetpoint@": f"{COOLING_SETPOINT}",
        "@ventilationRate@": f"{VENTILATION_RATE}",
        "@internalMass@": f"{INTERNAL_MASS}",
        "@numPeople_101@": f"{people_per_zone:.6f}",
        "@numPeople_102@": f"{people_per_zone:.6f}",
        "@2height@": f"{2 * H}",
        "@length/2@": f"{L / 2}",
    }
    for name, band in [("north", north), ("south_u", south_upper), ("south_g", south_ground)]:
        for i, x in enumerate(band, start=1):
            values[f"@window{name}_x{i}@"] = f"{x:.6f}"
    values |= {
        "@windowEast_y1@": f"{side_y1:.6f}",
        "@windowEast_y2@": f"{side_y2:.6f}",
        "@window_z1@": f"{z1:.6f}",
        "@window_z2@": f"{z2:.6f}",
        "@windowOpeningArea_S_101@": f"{wof * area_south_ground:.8f}",
        "@windowOpeningArea_S_102@": f"{wof * area_south_upper:.8f}",
        "@windowOpeningArea_N@": f"{wof * area_north:.8f}",
        "@windowOpeningArea_E@": f"{wof * area_side:.8f}",
        "@windowOpeningArea_W@": f"{wof * area_side:.8f}",
        "@daylightReference_x@": f"{W / 2}",
        "@daylightReference_y@": f"{L / 2}",
    }
    return values
