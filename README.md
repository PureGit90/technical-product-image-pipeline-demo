# Technical Product Image Pipeline -- Working Automation Demo

## What This Does
Turns structured product data into consistent technical catalog images. Each SKU that is missing an image is routed to the right generator (parametric SVG, CAD line-art, or AI-assisted generation), and the SVG path draws dimensioned technical diagrams directly from the attributes.

## How It Works
Batch trigger -> product attributes (CSV here, Magento API in production) -> route each SKU (CAD, SVG, or AI) -> render and attach image -> processing log plus error queue for bad data

## Quick Start
1. `pip install -r requirements.txt`
2. `streamlit run app.py`
3. Click "Generate images" to render diagrams for the sample catalog. Pick a SKU in the failure dropdown to see error tracking. Upload your own CSV with the same columns to try other data.

## Configuration
- Runs fully on sample data. No API keys needed.

## Demo Limitations
- Three SVG templates (flat plate, bushing, L-bracket). CAD and AI paths are routed and queued but not executed here.
- Production version would add: live Magento API read/write, STEP-to-line-art projection, AI generation for products without CAD, background cleanup and vectorization, and a style-review step.
