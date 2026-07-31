"""Public/private export boundary tests for live-smoke assets."""

from __future__ import annotations

import sys


def test_private_live_smoke_assets_are_excluded_from_public_export(
    live_smoke,
) -> None:
    import yaml

    release_dir = live_smoke.root / ".release"
    if str(release_dir) not in sys.path:
        sys.path.insert(0, str(release_dir))
    import export_public

    manifest = yaml.safe_load(
        (release_dir / "public-manifest.yaml").read_text(encoding="utf-8")
    )
    exported = {
        path.relative_to(live_smoke.root).as_posix()
        for path in export_public.collect_files(manifest)
    }
    private_runtime = {
        "examples/runtime/openai_responses_live_smoke.py",
        "examples/runtime/openai_responses_live_smoke_audit.py",
        "examples/runtime/openai_responses_live_smoke_environment.py",
        "examples/runtime/openai_responses_live_smoke_evidence.py",
        "examples/runtime/openai_responses_live_smoke_closure.py",
        "examples/runtime/openai_responses_live_smoke_closure_verifier.py",
    }
    assert private_runtime.isdisjoint(exported)
    assert "tests/test_openai_responses_live_smoke_audit.py" not in exported
    assert not any(
        path.startswith("tests/private_openai_live_smoke/") for path in exported
    )
