"""Interactive results of the BSO-uSIM 2026 overheating surrogate study.

streamlit run app/streamlit_app.py
"""

import streamlit as st
from streamlit.components.v1 import html

from common import DISCLAIMER

st.set_page_config(page_title="Overheating design explorer", page_icon=":material/home_work:", layout="wide")

# Browser page translation (Chrome Translate, translation extensions) rewrites text nodes that React still
# manages, which crashes the app with "Failed to execute 'removeChild' on 'Node'". Ask browsers not to translate.
with st.sidebar:
    html(
        """<script>
        const doc = window.parent.document;
        doc.documentElement.setAttribute("translate", "no");
        doc.documentElement.classList.add("notranslate");
        if (!doc.querySelector('meta[name="google"]')) {
          const meta = doc.createElement("meta");
          meta.name = "google";
          meta.content = "notranslate";
          doc.head.appendChild(meta);
        }
        </script>""",
        height=0,
    )

pages = st.navigation(
    {
        "Tool": [st.Page("pages/design.py", title="Design explorer", icon=":material/home_work:", default=True)],
        "Research": [
            st.Page("pages/overview.py", title="Research overview", icon=":material/article:"),
            st.Page("pages/weather.py", title="Weather comparison", icon=":material/thermostat:"),
            st.Page("pages/explorer.py", title="Simulated cases", icon=":material/scatter_plot:"),
            st.Page("pages/evaluation.py", title="Model evaluation", icon=":material/analytics:"),
            st.Page("pages/explainability.py", title="Explainability", icon=":material/insights:"),
        ],
    }
)
pages.run()
st.divider()
st.caption(DISCLAIMER)
