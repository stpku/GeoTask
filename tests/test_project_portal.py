import re
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

import yaml


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PORTAL = SITE / "index.html"
GT01 = SITE / "gt01" / "index.html"
ROBOTS = SITE / "robots.txt"
SITEMAP = SITE / "sitemap.xml"
README = SITE / "README.md"
DEPLOY_SCRIPT = SITE / "deploy-nginx.sh"
MANIFEST = ROOT / ".release" / "public-manifest.yaml"


def test_root_page_is_project_portal_not_gt01_experience() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    assert "面向AI智能体的" in html
    assert "可验证时空任务协议" in html
    assert "模型会回答，系统还要验证" in html
    assert "开放Core，连接时空智能生态" in html
    assert "当前已开放" in html
    assert "持续建设" in html
    assert "保护商业运行层" not in html
    assert "商业边界" not in html
    assert "GT01—GT20渐进式案例" in html
    assert 'id="cases"' in html
    assert 'id="architecture"' in html
    assert 'id="docs"' in html

    assert 'id="copy-open"' not in html
    assert 'id="task-source"' not in html
    assert 'id: "minimal-distance-v1"' not in html


def test_portal_links_all_public_cases() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    for number in range(1, 21):
        case = f"gt{number:02d}/"
        assert f'href="{case}"' in html
        assert f"GT{number:02d}" in html


def test_portal_links_primary_public_resources() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    required = (
        "https://github.com/stpku/GeoTask",
        "docs/whitepaper/GeoTask_White_Paper_v0.1.md",
        "docs/spec/geotask-language-spec-v1.0.md",
        "docs/tutorials/quickstart.zh-CN.md",
        "docs/cookbook/gt01-gt20.zh-CN.md",
        "schemas/geotask-v1.0.schema.json",
    )
    for fragment in required:
        assert fragment in html


def test_portal_has_search_and_share_metadata() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    required = (
        '<link rel="canonical" href="https://stpku.github.io/GeoTask/">',
        '<link rel="sitemap" type="application/xml" href="sitemap.xml">',
        '<meta property="og:title"',
        '<meta property="og:description"',
        '<meta property="og:url" content="https://stpku.github.io/GeoTask/">',
        '<meta name="twitter:card" content="summary">',
        '<script type="application/ld+json">',
        '"@type": "SoftwareSourceCode"',
    )
    for fragment in required:
        assert fragment in html


def test_portal_is_static_and_secret_free() -> None:
    html = PORTAL.read_text(encoding="utf-8").lower()

    assert "<script src=" not in html
    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt01_moved_to_stable_nested_route() -> None:
    html = GT01.read_text(encoding="utf-8")

    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert 'id="task-source"' in html
    assert 'id: "minimal-distance-v1"' in html
    assert "ab_distance = 5.0 meter" in html
    assert 'href="../"' in html
    assert "项目首页" in html
    assert 'href="../gt02/"' in html
    assert 'href="https://stpku.github.io/GeoTask/gt01/"' in html


def test_all_case_pages_link_back_to_project_portal() -> None:
    for number in range(1, 21):
        path = SITE / f"gt{number:02d}" / "index.html"
        assert path.is_file(), path
        html = path.read_text(encoding="utf-8")
        assert 'aria-label="返回GeoTask项目首页"' in html or (
            number == 1 and 'class="home" href="../">项目首页</a>' in html
        )


def test_all_site_relative_links_resolve_under_project_subpath() -> None:
    missing: list[tuple[str, str]] = []

    for path in SITE.rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        for raw_target in re.findall(r'href="([^"]+)"', html):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            if resolved.is_dir():
                resolved = resolved / "index.html"
            if not resolved.exists():
                missing.append((path.relative_to(ROOT).as_posix(), raw_target))

    assert missing == []


def test_robots_and_sitemap_cover_portal_and_all_cases() -> None:
    robots = ROBOTS.read_text(encoding="utf-8")
    assert "User-agent: *" in robots
    assert "Allow: /" in robots
    assert "https://stpku.github.io/GeoTask/sitemap.xml" in robots

    root = ElementTree.parse(SITEMAP).getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {node.text for node in root.findall("sm:url/sm:loc", namespace)}
    expected = {"https://stpku.github.io/GeoTask/"}
    expected.update(
        f"https://stpku.github.io/GeoTask/gt{number:02d}/"
        for number in range(1, 21)
    )
    assert urls == expected


def test_deployment_checks_portal_gt01_and_search_files() -> None:
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    assert "Missing GeoTask project portal" in script
    assert 'test -f "$TARGET/index.html"' in script
    assert 'test -f "$TARGET/gt01/index.html"' in script
    assert 'test -f "$TARGET/gt14/index.html"' in script
    assert 'test -f "$TARGET/gt15/index.html"' in script
    assert 'test -f "$TARGET/gt16/index.html"' in script
    assert 'test -f "$TARGET/gt17/index.html"' in script
    assert 'test -f "$TARGET/gt18/index.html"' in script
    assert 'test -f "$TARGET/gt19/index.html"' in script
    assert 'test -f "$TARGET/gt20/index.html"' in script
    assert 'test -f "$TARGET/robots.txt"' in script
    assert 'test -f "$TARGET/sitemap.xml"' in script
    assert "Portal: $TARGET/index.html" in script
    assert "GT01: $TARGET/gt01/index.html" in script

    assert "GitHub Pages是公共Canonical入口" in readme
    assert "site/gt01/index.html" in readme
    assert "https://stpku.github.io/GeoTask/gt01/" in readme
    assert "不再把根地址当作GT01" in readme


def test_public_manifest_requires_portal_routes_and_search_files() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    required = set(manifest["required"])
    expected = {
        "site/index.html",
        "site/gt01/index.html",
        "site/gt14/index.html",
        "site/gt15/index.html",
        "site/gt16/index.html",
        "site/gt17/index.html",
        "site/gt18/index.html",
        "site/gt19/index.html",
        "site/gt20/index.html",
        "site/robots.txt",
        "site/sitemap.xml",
        ".github/workflows/pages.yml",
    }
    assert expected <= required
