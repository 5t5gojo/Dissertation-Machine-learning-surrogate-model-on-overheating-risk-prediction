"""Interactive results of the BSO-uSIM 2026 overheating surrogate study.

streamlit run app/streamlit_app.py
"""

import streamlit as st
from streamlit.components.v1 import html

from common import DISCLAIMER

st.set_page_config(page_title="Overheating design explorer", page_icon=":material/home_work:", layout="wide")

# Browser page translation (Chrome Translate, translation extensions) replaces text nodes that React still
# manages, so React later fails with "Failed to execute 'removeChild' on 'Node'". Let removeChild and
# insertBefore skip nodes the translator has already moved, so translated pages keep working.
with st.sidebar:
    html(
        """<script>
        const P = window.parent;
        if (!P.__translationSafe) {
          P.__translationSafe = true;
          const remove = P.Node.prototype.removeChild;
          P.Node.prototype.removeChild = function (child) {
            if (child.parentNode !== this) return child;
            return remove.apply(this, arguments);
          };
          const insert = P.Node.prototype.insertBefore;
          P.Node.prototype.insertBefore = function (node, reference) {
            if (reference && reference.parentNode !== this) return node;
            return insert.apply(this, arguments);
          };
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
