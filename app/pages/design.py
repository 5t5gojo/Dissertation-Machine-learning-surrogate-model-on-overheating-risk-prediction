import math

import numpy as np
import streamlit as st

import house
from common import ARCHETYPES, FEATURES, TARGETS, WEATHER_COLOURS, dataset, parameter_bounds, result, surrogate

WEATHER_NAMES = {"TMYx": "Typical year (TMYx)", "DSY1": "Hot summer 2030s (DSY1)"}
KEY_INPUTS = ["wwr", "g_value", "wof", "orientation", "fixedShadingDepth"]
ADVANCED = {
    "Geometry": ["width", "length", "height"],
    "Fabric": ["wallInsulationThickness", "roofInsulationThickness", "slabInsulationThickness", "u_windows",
               "roofAbsorptance"],
    "Airtightness": ["flowCoefficient"],
}  # fmt: skip
HELP = {
    "wwr": "Sampled window-to-wall ratio of each facade. Glazing that does not fit between margins, mullions and the "
    "door is clipped, as in the EnergyPlus model.",
    "g_value": "Solar energy transmittance of the glazing. Drawn as glass tint.",
    "wof": "Openable share of the glazed area when windows are opened for cooling.",
    "orientation": "Clockwise rotation of the house (EnergyPlus North Axis). At 0° the front door faces south.",
    "fixedShadingDepth": "Depth of the horizontal overhang 0.5 m above every window.",
    "roofAbsorptance": "Solar absorptance of the roof. Drawn as roof shade.",
}
FORMATS = {"He_worst": "{:.1f}", "We_max_worst": "{:.1f}", "T_op_peak": "{:.1f}", "hours_gt26_night": "{:.0f}",
           "heat_kWh_m2": "{:.1f}"}  # fmt: skip
NON_NEGATIVE = ("He_worst", "We_max_worst", "hours_gt26_night")

bounds = parameter_bounds()
MIDPOINT = {feature: (low + high) / 2 for feature, (low, high) in bounds.items()} | {"orientation": 0.0}
PRESETS = {
    "Mid-range design": {},
    "High solar gain": {"wwr": 0.40, "g_value": 0.70, "fixedShadingDepth": 0.0, "wof": 0.10},
    "Improved glazing and shading": {"u_windows": 1.2, "g_value": 0.30, "fixedShadingDepth": 0.8, "wof": 0.60},
}

st.markdown(
    """
<style>
.block-container {padding-top: 2.2rem;}
.oh-head {display: flex; align-items: center; gap: 12px; flex-wrap: wrap;}
.oh-head h1 {font-size: 1.9rem; margin: 0; padding: 0;}
.oh-badge {font-size: .75rem; font-weight: 600; color: #0B7A9E; border: 1px solid #0B7A9E; border-radius: 999px;
           padding: 2px 10px; white-space: nowrap;}
.oh-sub {color: #5f6670; margin: 4px 0 2px; font-size: .95rem;}
.oh-card {border: 1px solid #E3E6EA; border-radius: 10px; padding: 10px 14px 8px; margin-bottom: 10px;
          background: #FFFFFF;}
.oh-name {font-size: .86rem; color: #2f353b; font-weight: 600;}
.oh-unit {color: #6b7280; font-weight: 400;}
.oh-row {display: flex; gap: 22px; align-items: baseline; margin-top: 2px; flex-wrap: wrap;}
.oh-w {font-size: .74rem; color: #5f6670; display: inline-flex; align-items: center; gap: 5px; margin-right: 6px;}
.oh-key {width: 9px; height: 9px; border-radius: 50%; display: inline-block;}
.oh-v {font-size: 1.45rem; font-weight: 600; color: #1f2328; font-variant-numeric: tabular-nums;}
.oh-d {font-size: .78rem; margin-left: 4px; font-variant-numeric: tabular-nums;}
.oh-up {color: #B42318;} .oh-down {color: #067647;} .oh-same {color: #6b7280;}
.oh-track {position: relative; height: 6px; background: #EEF0F2; border-radius: 3px; margin: 10px 6px 3px;}
.oh-dot {position: absolute; top: -4px; width: 14px; height: 14px; border-radius: 50%;
         transform: translateX(-50%); border: 2px solid #FFFFFF; box-sizing: border-box;}
.oh-ghost {background: #FFFFFF !important; border-width: 2px; border-style: solid;}
.oh-foot {display: flex; justify-content: space-between; font-size: .72rem; color: #6b7280; gap: 8px;}
.oh-flag {font-size: .85rem; margin: 2px 0;}
</style>
""",
    unsafe_allow_html=True,
)


def step_of(feature: str) -> float:
    """Power-of-ten slider step giving at least 100 positions across the range."""
    low, high = bounds[feature]
    return 10.0 ** math.floor(math.log10((high - low) / 100))


def snap(feature: str, value: float) -> float:
    low, high = bounds[feature]
    decimals = max(0, round(-math.log10(step_of(feature))))
    return min(max(round(round(value / step_of(feature)) * step_of(feature), decimals), low), high)


def apply_preset() -> None:
    values = MIDPOINT | PRESETS[st.session_state.preset]
    for feature in FEATURES:
        st.session_state[f"x_{feature}"] = snap(feature, values[feature])


def slider(container, feature: str) -> None:
    name, unit = FEATURES[feature]
    low, high = bounds[feature]
    container.slider(
        f"{name} ({unit})" if unit else name,
        min_value=float(low),
        max_value=float(high),
        step=step_of(feature),
        format="%.4g" if high < 0.1 else "%.3g",
        key=f"x_{feature}",
        help=HELP.get(feature),
    )


def predict(design: dict, archetype: str) -> dict[tuple[str, str], float]:
    x = np.array([[design[feature] for feature in FEATURES]])
    values = {}
    for weather in WEATHER_NAMES:
        for target in TARGETS:
            value = float(surrogate(weather, archetype, target).inplace_predict(x)[0])
            values[weather, target] = max(value, 0.0) if target in NON_NEGATIVE else value
    return values


def compass(azimuth: float) -> str:
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return points[round(azimuth / 22.5) % 16]


# Widget state is dropped while another page is open, so restore the last design from a plain copy.
saved = st.session_state.get("saved_design")
if "x_width" not in st.session_state:
    if saved:
        st.session_state.preset = saved["preset"]
        for feature, value in saved["inputs"].items():
            st.session_state[f"x_{feature}"] = value
    else:
        st.session_state.preset = "Mid-range design"
        apply_preset()
if "tool_archetype" not in st.session_state:
    st.session_state.tool_archetype = saved["archetype"] if saved else "detached"

st.markdown(
    '<div class="oh-head"><h1>Overheating design explorer</h1><span class="oh-badge">Research prototype</span></div>'
    '<p class="oh-sub">Change a house design and see how the EnergyPlus-trained XGBoost surrogates predict summer '
    "overheating and heating demand under a typical London year and a 2030s hot summer, in milliseconds instead of "
    "a full simulation.</p>",
    unsafe_allow_html=True,
)
st.caption(
    "Surrogate estimates of EnergyPlus results for a simplified two-storey model, not measured temperatures. "
    "The overheating indicators are TM52/TM59-derived screening proxies, not compliance results."
)

view, options, outcomes = st.columns([5, 4, 5], gap="large")

with options:
    st.markdown("#### Design options")
    archetype = st.segmented_control(
        "House type", list(ARCHETYPES), format_func=ARCHETYPES.get, key="tool_archetype", width="stretch"
    )
    archetype = archetype or "detached"
    st.selectbox(
        "Start from a scenario",
        list(PRESETS),
        key="preset",
        on_change=apply_preset,
        help="Scenarios start from mid-range values with the front facing south and change a few window-related "
        "inputs. They illustrate the model's behaviour and are not statistically typical homes.",
    )
    for feature in KEY_INPUTS:
        slider(st, feature)
    with st.expander("Advanced settings: geometry, fabric, airtightness"):
        for group, features in ADVANCED.items():
            st.markdown(f"**{group}**")
            for feature in features:
                slider(st, feature)

design = {feature: st.session_state[f"x_{feature}"] for feature in FEATURES}
st.session_state.saved_design = {"inputs": design, "archetype": archetype, "preset": st.session_state.preset}
current = predict(design, archetype)
pinned = st.session_state.get("pinned")

with view:
    st.markdown("#### Building")
    st.plotly_chart(
        house.figure(design, archetype, pinned["design"] if pinned else None),
        width="stretch",
        key="house_view",
        config={"displayModeBar": False},
    )
    front = (180 + design["orientation"]) % 360
    realised = house.realised_wwr(design, archetype)
    notes = [f"Front door facade faces **{compass(front)}** ({front:.0f}°)."]
    if realised < design["wwr"] - 0.005:
        notes.append(
            f"Glazing is clipped to fit, so the drawn ratio is {realised:.2f} (model input {design['wwr']:.2f})."
        )
    notes.append("Glass tint follows the g-value and roof shade the roof absorptance. Drag to rotate.")
    if archetype == "semi":
        notes.append("The attached neighbour (grey) makes the east wall adiabatic.")
    if pinned:
        notes.append("The dashed red outline is the pinned design A.")
    st.caption(" ".join(notes))

with outcomes:
    st.markdown("#### Predicted performance")
    pin, clear = st.columns(2)
    if pin.button("Pin as A", icon=":material/push_pin:", width="stretch"):
        st.session_state.pinned = {"design": dict(design), "archetype": archetype, "values": dict(current)}
        st.rerun()
    if clear.button("Clear pin", icon=":material/close:", width="stretch", disabled=pinned is None):
        st.session_state.pop("pinned", None)
        st.rerun()

    if pinned:
        changed = [FEATURES[f][0].lower() for f in FEATURES if abs(design[f] - pinned["design"][f]) > 1e-9]
        if pinned["archetype"] != archetype:
            changed.insert(0, "house type")
        st.caption(
            "Arrows compare this design with A"
            + (f" (changed: {', '.join(changed)})." if changed else ", which has the same inputs.")
            + " Differences are between two surrogate predictions with everything else fixed, not measured savings."
        )

    cards = []
    for target, (name, unit) in TARGETS.items():
        fmt = FORMATS[target]
        simulated = np.concatenate([dataset(w, archetype)[target].to_numpy() for w in WEATHER_NAMES])
        low, high = (float(v) for v in np.percentile(simulated, [1, 99]))

        def position(value: float, low: float = low, high: float = high) -> float:
            return 100 * min(max((value - low) / (high - low), 0.0), 1.0)

        values, dots = [], []
        for weather in WEATHER_NAMES:
            value, colour = current[weather, target], WEATHER_COLOURS[weather]
            delta = ""
            if pinned:
                change = value - pinned["values"][weather, target]
                shown = fmt.format(abs(change))
                if float(shown) == 0:
                    delta = '<span class="oh-d oh-same">no change</span>'
                else:
                    arrow, css = ("▲ +", "oh-up") if change > 0 else ("▼ −", "oh-down")
                    delta = f'<span class="oh-d {css}">{arrow}{shown}</span>'
                dots.append(
                    f'<span class="oh-dot oh-ghost" style="left:{position(pinned["values"][weather, target]):.1f}%;'
                    f'border-color:{colour}" title="A, {weather}"></span>'
                )
            values.append(
                f'<span><span class="oh-w"><span class="oh-key" style="background:{colour}"></span>{weather}</span>'
                f'<span class="oh-v">{fmt.format(value)}</span>{delta}</span>'
            )
            dots.append(
                f'<span class="oh-dot" style="left:{position(value):.1f}%;background:{colour}" '
                f'title="{weather}"></span>'
            )
        cards.append(
            f'<div class="oh-card"><div class="oh-name">{name} <span class="oh-unit">{unit}</span></div>'
            f'<div class="oh-row">{"".join(values)}</div>'
            f'<div class="oh-track">{"".join(dots)}</div>'
            f'<div class="oh-foot"><span>{fmt.format(low)}</span><span>1st–99th percentile of simulated runs'
            f"{' (hollow: A)' if pinned else ''}</span><span>{fmt.format(high)}</span></div></div>"
        )
    st.markdown("".join(cards), unsafe_allow_html=True)
    st.caption("Lower is better for all five outcomes.")

    lines = []
    for weather in WEATHER_NAMES:
        he, we = current[weather, "He_worst"], current[weather, "We_max_worst"]
        flagged = [
            text
            for text, hit in [(f"Hₑ {he:.2f} % above 3 %", he > 3), (f"Wₑ {we:.2f} K h above 6 K h", we > 6)]
            if hit
        ]
        status = "⚠️ " + " and ".join(flagged) if flagged else "✓ below both thresholds"
        lines.append(f'<div class="oh-flag"><b>{weather}</b>: {status}</div>')
    st.markdown("**TM52-derived screening flags**" + "".join(lines), unsafe_allow_html=True)

    if max(current["TMYx", "hours_gt26_night"], current["DSY1", "hours_gt26_night"]) > 25:
        st.info(
            "This prediction is in the high night-time exposure range. On held-out test designs, the surrogates "
            "systematically underpredicted designs whose simulated night hours were highest, so treat high "
            "predictions as a lower-confidence screening signal."
        )

    with st.expander("How reliable are these numbers?"):
        rows = []
        for target, (name, unit) in TARGETS.items():  # noqa: B007 (target is used in the query)
            rmse = []
            for weather in WEATHER_NAMES:
                scores = result(weather, "performance").query(
                    "archetype == @archetype and model == 'XGBoost' and target == @target and seed == 42"
                )
                rmse.append(f"{float(scores.RMSE.iloc[0]):.2f}")
            rows.append(f"| {name} | {unit} | {rmse[0]} | {rmse[1]} |")
        st.markdown(
            "| Outcome | Unit | TMYx test RMSE | DSY1 test RMSE |\n| --- | --- | --- | --- |\n" + "\n".join(rows)
        )
        st.markdown(
            "Held-out test RMSE summarises the average squared-error magnitude across the test designs of split 42. "
            "It is not a prediction interval for this specific design.\n\n"
            "Staying within each input's range does not guarantee that a combination of inputs is representative "
            "of the UK housing stock.\n\n"
            "The models were trained separately for each weather file and each house type, so a comparison between "
            "the two columns is a comparison between two surrogates."
        )
        st.page_link("pages/evaluation.py", label="Model evaluation across five splits", icon=":material/analytics:")
