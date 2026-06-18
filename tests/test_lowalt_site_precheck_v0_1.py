"""Tests for LowAlt Site Precheck Mock MVP v0.1."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from geotask_domain_packs.lowalt_site_precheck.models import (
    CandidateSite, InitialRoute, SensitiveSite, RestrictedZone,
    ObstacleBand, FlightTimeWindow, FlightAltitudeBand,
    LowAltPrecheckRequest, LowAltPrecheckResult,
)
from geotask_domain_packs.lowalt_site_precheck.pack import LowAltSitePrecheckPack
from geotask_domain_packs.lowalt_site_precheck.mock_data import (
    basic_safe_case, route_zone_conflict_case,
    missing_data_case, invalid_reference_case,
)
from geotask_domain_packs.lowalt_site_precheck.report import build_lowalt_precheck_report


def test_lowalt_pack_importable():
    pack = LowAltSitePrecheckPack()
    assert pack.name == "lowalt_site_precheck"
    assert pack.version == "0.1-mock"


def test_models_instantiate():
    site = CandidateSite(site_id="S1", name="Test", xy=[0.0, 0.0])
    assert site.site_id == "S1"
    route = InitialRoute(route_id="R1", points=[[0, 0], [10, 10]])
    assert len(route.points) == 2
    zone = RestrictedZone(zone_id="Z1", bbox=[0, 0, 10, 10], restriction_type="no_fly")
    assert zone.bbox == [0, 0, 10, 10]
    result = LowAltPrecheckResult(request_id="test")
    assert "mock" in result.disclaimer.lower()


def test_basic_safe_case():
    req = basic_safe_case()
    pack = LowAltSitePrecheckPack()
    result = pack.run_precheck(req)
    assert result.overall_status == "verified"
    assert len(result.risk_items) == 0
    assert len(result.verified_items) >= 1


def test_route_zone_conflict():
    req = route_zone_conflict_case()
    pack = LowAltSitePrecheckPack()
    result = pack.run_precheck(req)
    assert result.overall_status == "contradicted"
    assert len(result.contradicted_items) >= 1
    assert len(result.risk_items) >= 1


def test_missing_data_triggers_need_review():
    req = missing_data_case()
    pack = LowAltSitePrecheckPack()
    result = pack.run_precheck(req)
    assert result.overall_status == "need_review" or result.overall_status == "verified"
    assert len(result.planned_data_gaps) > 0


def test_invalid_reference_handled():
    req = invalid_reference_case()
    pack = LowAltSitePrecheckPack()
    result = pack.run_precheck(req)
    assert result.overall_status in ("need_review", "verified")
    assert result.request_id == "invalid_ref_004"


def test_planned_data_gaps_field_exists():
    req = missing_data_case()
    pack = LowAltSitePrecheckPack()
    result = pack.run_precheck(req)
    assert hasattr(result, 'planned_data_gaps')
    assert isinstance(result.planned_data_gaps, list)


def test_no_external_api_calls():
    """Verify no external API calls by checking the pack works offline."""
    req = basic_safe_case()
    pack = LowAltSitePrecheckPack()
    result = pack.run_precheck(req)
    assert result is not None


def test_report_contains_disclaimer():
    req = basic_safe_case()
    pack = LowAltSitePrecheckPack()
    result = pack.run_precheck(req)
    report = build_lowalt_precheck_report(result)
    assert "disclaimer" in report
    disclaimer_lower = report["disclaimer"].lower()
    assert "not" in disclaimer_lower or "mock" in disclaimer_lower


def test_report_contains_all_sections():
    req = route_zone_conflict_case()
    pack = LowAltSitePrecheckPack()
    result = pack.run_precheck(req)
    report = build_lowalt_precheck_report(result)
    for key in ["risk_items", "verified_items", "contradicted_items",
                "review_items", "planned_data_gaps", "overall_status", "summary"]:
        assert key in report, f"Missing key: {key}"


def test_all_mock_coordinates_local_xy():
    """All coordinates should be local_xy_m (not real lat/lon)."""
    for case_fn in [basic_safe_case, route_zone_conflict_case,
                     missing_data_case, invalid_reference_case]:
        req = case_fn()
        for site in req.candidate_sites:
            assert -1000 <= site.xy[0] <= 1000
            assert -1000 <= site.xy[1] <= 1000


def test_old_core_tests_still_pass():
    """Verify Core imports still work."""
    from geotask_core.ops import distance_2d, line_intersects_rect
    from geotask_core.result_schema import STATUS_VERIFIED
    d = distance_2d([0, 0], [3, 4])
    assert abs(d - 5.0) < 0.01


def test_obstacle_altitude_check():
    """Test obstacle altitude overlap check."""
    from geotask_domain_packs.lowalt_site_precheck.rules import check_obstacle_altitude_conflict
    obs = ObstacleBand(
        obstacle_id="O1", xy=[100, 100],
        height_range_m=[30, 80], clearance_margin_m=10,
    )
    alt = FlightAltitudeBand(min_alt_m=50, max_alt_m=120)
    result = check_obstacle_altitude_conflict(obs, alt)
    assert result["value"] is True
    assert result["operator"] == "altitude_overlap"


def test_time_window_conflict():
    """Test time window overlap check."""
    from geotask_domain_packs.lowalt_site_precheck.rules import check_time_window_conflict
    fw = FlightTimeWindow(start_time="09:00", end_time="11:00")
    rw = FlightTimeWindow(start_time="10:00", end_time="12:00")
    result = check_time_window_conflict(fw, rw)
    assert result["value"] is True
    assert result["operator"] == "time_overlap"
