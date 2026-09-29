import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from image_pipeline import load_products, needs_image, route, run_batch

st.set_page_config(page_title="Technical Product Image Pipeline", page_icon="📐", layout="wide")

st.title("Technical Product Image Pipeline")
st.write(
    "A hybrid catalog-image workflow: product attributes go in, and each SKU is routed to "
    "parametric SVG, CAD line-art, or AI-assisted generation. SVG diagrams are drawn "
    "straight from the data, so every image in a family looks identical."
)

uploaded = st.file_uploader("Upload a product export (CSV), or use the sample catalog", type="csv")
products = load_products(uploaded) if uploaded else load_products()

st.subheader("1. Catalog snapshot")
df = pd.DataFrame(products)
df["needs_image"] = [needs_image(p) for p in products]
df["route"] = [route(p)[0] if needs_image(p) else "-" for p in products]
st.dataframe(df[["sku", "name", "family", "needs_image", "route", "step_file", "current_image"]], width='stretch')

c1, c2, c3, c4 = st.columns(4)
missing = [p for p in products if needs_image(p)]
c1.metric("SKUs in catalog", len(products))
c2.metric("Missing images", len(missing))
c3.metric("Routed to SVG", sum(1 for p in missing if route(p)[0] == "SVG"))
c4.metric("Routed to CAD / AI", sum(1 for p in missing if route(p)[0] != "SVG"))

st.subheader("2. Run the batch")
fail = st.selectbox("Simulate an API failure on one SKU (to show error tracking)", ["None"] + [p["sku"] for p in missing])
if st.button("Generate images"):
    results, log = run_batch(products, fail_sku=None if fail == "None" else fail)
    ok = [r for r in results if r["status"] == "ok"]
    queued = [r for r in results if r["status"] == "queued"]
    errs = [r for r in results if r["status"] == "error"]
    st.success(f"{len(ok)} rendered, {len(queued)} queued for CAD/AI workers, {len(errs)} need data correction")

    st.subheader("Rendered technical diagrams")
    cols = st.columns(3)
    for i, r in enumerate(ok):
        with cols[i % 3]:
            components.html(r["svg"], height=370)
            st.download_button(f"Download {r['sku']}.svg", r["svg"], file_name=f"{r['sku']}.svg", mime="image/svg+xml", key=r["sku"])

    if errs:
        st.subheader("Error tracking")
        st.dataframe(pd.DataFrame(errs)[["sku", "pipeline", "reason"]], width='stretch')

    with st.expander("Processing log", expanded=True):
        st.code("\n".join(log), language=None)

st.caption(
    "Sample catalog and mock Magento data. Production version reads attributes from the Magento API "
    "and writes the finished image back to each SKU."
)
