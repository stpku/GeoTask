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

    assert "智能体的可验证" in html
    assert "时空世界模型" in html
    assert "让大模型理解世界，让GeoTask验证并维护世界" in html
    assert "智能体不只需要理解世界，更需要一个可以验证的世界模型" in html
    assert "30秒看懂一次世界状态更新" in html
    assert "四个平面构成可验证时空世界模型" in html
    assert "六类能力共同维护智能体的世界" in html
    assert "Observation v0.1、World State v0.1、支持调用方显式同目标冲突策略的受限Observation Merge v0.1、State Transition v0.1、Verification Session v0.1、Discrepancy Report v0.1、Correction Request v0.1、Impact Graph v0.1、来源绑定的受限重算值推导、受限后继状态物化、Incremental Reevaluation Result v0.1" in html
    assert "自动差异计算、对象身份发现、未声明策略的歧义命题冲突消解、Impact Graph自动发现与传播执行以及受限推导方法扩展" in html
    assert "支持调用方显式同目标冲突策略的受限Observation Merge v0.1" in html
    assert "自动差异计算、Observation合并" not in html
    assert "保护商业运行层" not in html
    assert "商业边界" not in html
    assert "GT01—GT26渐进式案例" in html
    assert 'id="demo"' in html
    assert 'id="cases"' in html
    assert 'id="architecture"' in html
    assert 'id="docs"' in html

    assert 'id="copy-open"' not in html
    assert 'id="task-source"' not in html
    assert 'id: "minimal-distance-v1"' not in html


def test_portal_exposes_gt16_world_state_update_demo() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    for fragment in (
        "初始世界状态",
        "新Observation",
        "世界关系更新",
        "行动资格更新",
        "计划间隔120秒",
        "A机最新遥测显示延误40秒",
        "预测间隔缩至80秒",
        "间隔降至60秒",
        "世界模型不是一次性结论",
        'href="gt16/"',
    ):
        assert fragment in html


def test_portal_links_all_public_cases() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    for number in range(1, 27):
        case = f"gt{number:02d}/"
        assert f'href="{case}"' in html
        assert f"GT{number:02d}" in html


def test_portal_links_primary_public_resources() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    required = (
        "https://github.com/stpku/GeoTask",
        "docs/whitepaper/GeoTask_White_Paper_v0.1.md",
        "docs/spec/geotask-language-spec-v1.0.md",
        "docs/spec/geotask-world-state-v0.1.md",
        "docs/spec/geotask-state-transition-v0.1.md",
        "docs/spec/geotask-verification-session-v0.1.md",
        "docs/spec/geotask-discrepancy-report-v0.1.md",
        "docs/spec/geotask-correction-request-v0.1.md",
        "docs/spec/geotask-impact-graph-v0.1.md",
        "docs/spec/geotask-incremental-reevaluation-result-v0.1.md",
        "docs/tutorials/quickstart.zh-CN.md",
        "docs/cookbook/gt21-gt28.zh-CN.md",
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
    for number in range(1, 27):
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
        for number in range(1, 27)
    )
    assert urls == expected


def test_deployment_checks_portal_gt01_and_search_files() -> None:
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    case_slugs = (SITE / "cases.txt").read_text(encoding="utf-8").splitlines()

    assert 'CASE_LIST="$SOURCE/cases.txt"' in script
    assert 'mapfile -t CASE_SLUGS' in script
    assert 'require_file "$SOURCE/$slug/index.html"' in script
    assert 'require_file "$TARGET/$slug/index.html"' in script
    assert 'require_file "$TARGET/index.html"' in script
    assert 'require_file "$TARGET/robots.txt"' in script
    assert 'require_file "$TARGET/sitemap.xml"' in script
    assert "Portal: $TARGET/index.html" in script
    assert 'echo "  ${slug^^}: $TARGET/$slug/index.html"' in script
    assert case_slugs == [f"gt{number:02d}" for number in range(1, 27)]

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
        "site/gt21/index.html",
        "site/gt22/index.html",
        "site/gt23/index.html",
        "site/gt24/index.html",
        "site/gt25/index.html",
        "site/gt26/index.html",
        "site/robots.txt",
        "site/sitemap.xml",
        ".github/workflows/pages.yml",
    }
    assert expected <= required
