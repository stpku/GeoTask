from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT03_PAGE = ROOT / "site" / "gt03" / "index.html"


# ── 1. GT03 task integrity ────────────────────────────────────────────────

def test_gt03_page_contains_full_geotask_yaml() -> None:
    html = GT03_PAGE.read_text(encoding="utf-8")

    assert 'id: "gt03-multisegment-route-zone-intersection"' in html
    assert "[-200, 220]" in html
    assert "[100, 220]" in html
    assert "[100, 0]" in html
    assert "[400, 0]" in html
    assert "route_intersects_zone" in html
    assert 'operator: "line_intersects_rect"' in html
    assert 'object_refs: ["route", "zone"]' in html


# ── 2. SVG visualization ──────────────────────────────────────────────────

def test_gt03_page_contains_svg_visualization() -> None:
    html = GT03_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "P1" in html or "p1" in html
    assert "P2" in html or "p2" in html
    assert "P3" in html or "p3" in html
    assert "P4" in html or "p4" in html
    assert "polyline" in html.lower()
    assert "rect" in html.lower()


# ── 3. Local geometric execution ──────────────────────────────────────────

def test_gt03_page_implements_local_geometric_operators() -> None:
    html = GT03_PAGE.read_text(encoding="utf-8")

    assert "function segmentsIntersect" in html or "segmentsIntersect" in html
    assert "function lineIntersectsRect" in html or "lineIntersectsRect" in html
    assert "points.length - 1" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "model_generated" in html
    assert "local_deterministic" in html


# ── 4. Copy and model entry ───────────────────────────────────────────────

def test_gt03_page_has_copy_and_deepseek_entry() -> None:
    html = GT03_PAGE.read_text(encoding="utf-8")

    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


# ── 5. Static and security ────────────────────────────────────────────────

def test_gt03_page_is_static_and_secret_free() -> None:
    html = GT03_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


# ── 6. Navigation links ───────────────────────────────────────────────────

def test_gt03_page_has_back_navigation() -> None:
    html = GT03_PAGE.read_text(encoding="utf-8")

    # GT03 should link back to GT02 at minimum
    assert 'href="../gt02/' in html or 'href="../"' in html or '返回' in html
