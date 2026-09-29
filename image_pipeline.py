"""Hybrid technical product image pipeline (demo).

Decides, per SKU, whether a product image should come from parametric SVG,
CAD/STEP line-art, or AI-assisted generation, then renders the SVG path
directly from structured product attributes. Mirrors the Magento flow:
fetch products -> detect missing images -> route -> generate -> attach -> log.
"""
import csv
import io
from pathlib import Path

SVG_FAMILIES = {"flat_plate", "bushing", "l_bracket"}
FONT = "font-family='Helvetica,Arial,sans-serif' font-size='13' fill='#1a1a1a'"
LINE = "stroke='#1a1a1a' stroke-width='2' fill='none'"
DIM = "stroke='#c0392b' stroke-width='1.2' fill='none'"


def load_products(source=None):
    if source is None:
        source = Path(__file__).parent / "sample_data" / "products.csv"
    if isinstance(source, (str, Path)):
        text = Path(source).read_text()
    else:
        text = source.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def needs_image(p):
    return not (p.get("current_image") or "").strip()


def route(p):
    """Return (pipeline, reason). Order matters: CAD beats SVG beats AI."""
    if (p.get("step_file") or "").strip():
        return "CAD", "STEP file available, project to standardized line-art"
    if p["family"] in SVG_FAMILIES:
        return "SVG", f"family '{p['family']}' has a parametric template"
    return "AI", "no CAD asset and no SVG template, use AI-assisted generation"


def validate(p):
    """Return a list of attribute errors that block generation."""
    errors = []
    fam = p["family"]
    need = {
        "flat_plate": ["width_mm", "height_mm", "hole_dia_mm", "hole_count"],
        "bushing": ["outer_dia_mm", "inner_dia_mm", "length_mm"],
        "l_bracket": ["width_mm", "height_mm", "thickness_mm"],
    }.get(fam, [])
    for key in need:
        v = (p.get(key) or "").strip()
        if not v:
            errors.append(f"missing attribute: {key}")
            continue
        try:
            if float(v) <= 0:
                errors.append(f"non-positive value: {key}={v}")
        except ValueError:
            errors.append(f"non-numeric value: {key}={v}")
    if fam == "bushing" and not errors:
        if float(p["inner_dia_mm"]) >= float(p["outer_dia_mm"]):
            errors.append("inner_dia_mm must be smaller than outer_dia_mm")
    return errors


def _f(p, k):
    return float(p[k])


def _hdim(x1, x2, y, label):
    mid = (x1 + x2) / 2
    return (f"<line x1='{x1}' y1='{y}' x2='{x2}' y2='{y}' {DIM}/>"
            f"<line x1='{x1}' y1='{y-6}' x2='{x1}' y2='{y+6}' {DIM}/>"
            f"<line x1='{x2}' y1='{y-6}' x2='{x2}' y2='{y+6}' {DIM}/>"
            f"<text x='{mid}' y='{y-8}' text-anchor='middle' {FONT}>{label}</text>")


def _vdim(x, y1, y2, label):
    mid = (y1 + y2) / 2
    return (f"<line x1='{x}' y1='{y1}' x2='{x}' y2='{y2}' {DIM}/>"
            f"<line x1='{x-6}' y1='{y1}' x2='{x+6}' y2='{y1}' {DIM}/>"
            f"<line x1='{x-6}' y1='{y2}' x2='{x+6}' y2='{y2}' {DIM}/>"
            f"<text x='{x+10}' y='{mid}' {FONT}>{label}</text>")


def _wrap(body, sku, title):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 480 360' width='480' height='360'>"
            f"<rect width='480' height='360' fill='white'/>{body}"
            f"<text x='16' y='340' {FONT}>{sku}  |  {title}</text></svg>")


def render_svg(p):
    fam = p["family"]
    sku = p["sku"]
    if fam == "flat_plate":
        w, h, d, n = _f(p, "width_mm"), _f(p, "height_mm"), _f(p, "hole_dia_mm"), int(_f(p, "hole_count"))
        scale = min(300 / w, 200 / h)
        pw, ph, x0, y0 = w * scale, h * scale, 90, 60
        r = d * scale / 2
        holes = ""
        for i in range(n):
            cx = x0 + pw * (i + 1) / (n + 1)
            holes += f"<circle cx='{cx:.1f}' cy='{y0 + ph/2:.1f}' r='{r:.1f}' {LINE}/>"
        body = (f"<rect x='{x0}' y='{y0}' width='{pw:.1f}' height='{ph:.1f}' {LINE}/>{holes}"
                + _hdim(x0, x0 + pw, y0 + ph + 30, f"{w:g} mm")
                + _vdim(x0 - 30, y0, y0 + ph, f"{h:g} mm"))
        return _wrap(body, sku, f"Flat plate, {n} x hole {d:g} mm")
    if fam == "bushing":
        od, idm, ln = _f(p, "outer_dia_mm"), _f(p, "inner_dia_mm"), _f(p, "length_mm")
        scale = min(180 / od, 300 / ln)
        r_o, r_i, L = od * scale / 2, idm * scale / 2, ln * scale
        cx, cy = 110, 150
        body = (f"<circle cx='{cx}' cy='{cy}' r='{r_o:.1f}' {LINE}/><circle cx='{cx}' cy='{cy}' r='{r_i:.1f}' {LINE}/>"
                f"<rect x='250' y='{cy - r_o:.1f}' width='{L:.1f}' height='{2*r_o:.1f}' {LINE}/>"
                f"<line x1='250' y1='{cy - r_i:.1f}' x2='{250 + L:.1f}' y2='{cy - r_i:.1f}' stroke='#1a1a1a' stroke-dasharray='5,4'/>"
                f"<line x1='250' y1='{cy + r_i:.1f}' x2='{250 + L:.1f}' y2='{cy + r_i:.1f}' stroke='#1a1a1a' stroke-dasharray='5,4'/>"
                + _vdim(cx - r_o - 24, cy - r_o, cy + r_o, f"OD {od:g}")
                + _hdim(250, 250 + L, cy + r_o + 30, f"L {ln:g} mm")
                + f"<text x='{cx}' y='{cy + r_o + 30:.1f}' text-anchor='middle' {FONT}>ID {idm:g}</text>")
        return _wrap(body, sku, "Bushing, front and side view")
    if fam == "l_bracket":
        w, h, t = _f(p, "width_mm"), _f(p, "height_mm"), _f(p, "thickness_mm")
        scale = min(260 / w, 220 / h)
        pw, ph, th, x0, y0 = w * scale, h * scale, max(t * scale, 6), 120, 50
        pts = f"{x0},{y0} {x0+th},{y0} {x0+th},{y0+ph-th} {x0+pw},{y0+ph-th} {x0+pw},{y0+ph} {x0},{y0+ph}"
        body = (f"<polygon points='{pts}' {LINE}/>"
                + _hdim(x0, x0 + pw, y0 + ph + 30, f"{w:g} mm")
                + _vdim(x0 - 30, y0, y0 + ph, f"{h:g} mm")
                + f"<text x='{x0 + pw + 12}' y='{y0 + ph - th/2:.1f}' {FONT}>t {t:g}</text>")
        return _wrap(body, sku, "L-bracket, side profile")
    raise ValueError(f"no SVG template for family {fam}")


def run_batch(products, fail_sku=None):
    """Process every SKU missing an image. Returns (results, log)."""
    results, log = [], []
    for p in products:
        sku = p["sku"]
        if not needs_image(p):
            log.append(f"[skip]  {sku}: already has an image")
            results.append({"sku": sku, "status": "skipped", "pipeline": "-", "reason": "image exists", "svg": None})
            continue
        pipeline, reason = route(p)
        errors = validate(p) if pipeline == "SVG" else []
        if fail_sku and sku == fail_sku:
            errors = errors + ["simulated Magento API timeout while fetching attributes"]
        if errors:
            log.append(f"[error] {sku}: {'; '.join(errors)} -> queued for data correction")
            results.append({"sku": sku, "status": "error", "pipeline": pipeline, "reason": "; ".join(errors), "svg": None})
            continue
        svg = render_svg(p) if pipeline == "SVG" else None
        if svg:
            log.append(f"[ok]    {sku}: {pipeline} ({reason}) -> rendered -> attached to SKU {sku}")
        else:
            log.append(f"[queue] {sku}: {pipeline} ({reason}) -> queued for {pipeline} worker, image attaches when it finishes")
        results.append({"sku": sku, "status": "ok" if svg else "queued", "pipeline": pipeline, "reason": reason, "svg": svg})
    return results, log
