"""Minimal IDF reader and the three final corrections applied to every simulation input.

After placeholder substitution, the templates still need three fixes, applied here as
in-place field edits so that nothing else in the file changes:

1. Ventilation bearing: wind-driven opening areas are given an absolute bearing
   (object bearing + building north axis + zone north axis), so window openings rotate
   with the sampled orientation.
2. Interfloor slab: the ceiling/floor between the two occupied storeys uses a bare
   100 mm concrete slab, so sampled loft insulation is not applied between storeys.
3. Semi-detached attic party wall: the attic wall shared with the neighbour is adiabatic.

Every edit is checked against the expected original value, and the result is re-parsed
to prove that only the intended fields changed.
"""

from __future__ import annotations

import re

INTERFLOOR_CONSTRUCTION = "Audit_Interfloor_RC_100mm"
# Appended verbatim; the text is part of the simulated IDF bytes.
INTERFLOOR_DEFINITION = (
    "\n! Isolated audit variant: original concrete slab; no sampled loft insulation.\n"
    f"Construction,\n    {INTERFLOOR_CONSTRUCTION},\n    RC_Slab_100mm;\n"
)
VENTILATION_OBJECTS = {"detached": 8, "semi": 6}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse(text: str) -> list[dict]:
    """Split IDF text into objects, keeping each field's exact character span.

    Comments (``!`` to end of line) are blanked rather than removed so that spans still
    index into the original text.
    """
    clean = re.sub(r"![^\n]*", lambda match: " " * len(match[0]), text)
    objects, start = [], 0
    for terminator in re.finditer(";", clean):
        end = terminator.start()
        block = clean[start:end]
        bounds = [start - 1] + [start + comma.start() for comma in re.finditer(",", block)] + [end]
        fields, spans = [], []
        for left, right in zip(bounds[:-1], bounds[1:], strict=True):
            raw = clean[left + 1 : right]
            value = raw.strip()
            offset = len(raw) - len(raw.lstrip())
            fields.append(value)
            spans.append((left + 1 + offset, left + 1 + offset + len(value)))
        if fields[0]:
            objects.append({"fields": fields, "spans": spans})
        start = end + 1
    require(not clean[start:].strip(), "Unterminated IDF object")
    return objects


def apply_final_settings(text: str, archetype: str) -> str:
    """Apply the three corrections described in the module docstring."""
    require(archetype in VENTILATION_OBJECTS, f"Unknown archetype: {archetype}")
    objects = parse(text)
    by_name = {(o["fields"][0].lower(), o["fields"][1]): o for o in objects if len(o["fields"]) > 1}
    edits: list[tuple[dict, int, str]] = []

    # 1. Absolute bearing for every wind-and-stack opening.
    north_axis = float(next(o["fields"][2] for o in objects if o["fields"][0].lower() == "building"))
    vents = [o for o in objects if o["fields"][0].lower() == "zoneventilation:windandstackopenarea"]
    require(len(vents) == VENTILATION_OBJECTS[archetype], "Unexpected ventilation count")
    for vent in vents:
        fields = vent["fields"]
        zone = by_name["zone", fields[2]]["fields"]
        bearing = (float(fields[6]) + north_axis + float(zone[2] or 0)) % 360
        edits.append((vent, 6, f"{bearing:.12f}"))

    # 2. Bare concrete slab between the occupied storeys.
    require(
        by_name["construction", "Interior Ceiling"]["fields"][2:] == ["Roof Insulation", "RC_Slab_100mm"],
        "Ceiling assembly changed",
    )
    require(
        by_name["construction", "Interior Floor"]["fields"][2:] == ["RC_Slab_100mm", "Roof Insulation"],
        "Floor assembly changed",
    )
    for surface, construction, other in [
        ("Surface 6", "Interior Ceiling", "Surface 7"),
        ("Surface 7", "Interior Floor", "Surface 6"),
    ]:
        fields = by_name["buildingsurface:detailed", surface]["fields"]
        require(
            fields[3] == construction and fields[6:8] == ["Surface", other],
            "Unexpected interfloor boundary",
        )
        edits.append((by_name["buildingsurface:detailed", surface], 3, INTERFLOOR_CONSTRUCTION))

    # 3. Adiabatic attic party wall for the semi-detached house.
    if archetype == "semi":
        attic = by_name["buildingsurface:detailed", "Surface 16"]
        require(
            attic["fields"][4] == "Thermal Zone: Space 1" and attic["fields"][6] == "Outdoors",
            "Unexpected attic boundary",
        )
        edits += [(attic, 6, "Adiabatic"), (attic, 8, "NoSun"), (attic, 9, "NoWind")]

    # Patch from the end of the file backwards so earlier spans stay valid.
    result = text
    for start, end, value in sorted(((*o["spans"][i], v) for o, i, v in edits), reverse=True):
        result = result[:start] + value + result[end:]
    result += INTERFLOOR_DEFINITION

    expected = [list(o["fields"]) for o in objects]
    for o, i, value in edits:
        expected[objects.index(o)][i] = value
    expected.append(["Construction", INTERFLOOR_CONSTRUCTION, "RC_Slab_100mm"])
    require([o["fields"] for o in parse(result)] == expected, "Unintended IDF field change")
    return result
