"""Interactive results of the BSO-uSIM 2026 overheating surrogate study.

streamlit run app/streamlit_app.py
"""

import streamlit as st

from common import DISCLAIMER

st.set_page_config(page_title="Overheating surrogates", layout="wide")

pages = st.navigation(
    [
        st.Page("pages/overview.py", title="Overview", default=True),
        st.Page("pages/weather.py", title="Weather comparison"),
        st.Page("pages/evaluation.py", title="Model evaluation"),
        st.Page("pages/explainability.py", title="Explainability"),
        st.Page("pages/predictor.py", title="Surrogate predictor"),
    ]
)
pages.run()
st.divider()
st.caption(DISCLAIMER)
