"""LowAlt Site Precheck Pack — main orchestrator."""

from geotask_runtime.contracts import TaskContext, TaskRequest, VerificationPlan
from .models import LowAltPrecheckRequest, LowAltPrecheckResult
from .rules import (
    check_sensitive_site_distance,
    check_route_restricted_zone_conflict,
    check_site_in_restricted_zone,
    check_obstacle_altitude_conflict,
    check_time_window_conflict,
    identify_data_gaps,
)


class LowAltSitePrecheckPack:
    """MOCK LowAlt Site Precheck Domain Pack.

    Uses fictional local_xy_m data. Does NOT access real airspace,
    maps, obstacles, airports, or regulatory data. Does NOT provide
    flight authorization.
    """

    name: str = "lowalt_site_precheck"
    version: str = "0.1-mock"

    def enrich_context(
        self, request: TaskRequest, context: TaskContext
    ) -> TaskContext:
        """Enrich task context with lowalt-specific operators and data sources."""
        context.available_operators = [
            "distance_2d", "line_intersects_rect",
            "rect_contains_point", "point_to_line_distance_2d",
            "time_overlap", "altitude_overlap",
        ]
        context.available_data_sources = ["mock_local_xy_m"]
        return context

    def build_verification_plan(
        self, request: TaskRequest, context: TaskContext
    ) -> VerificationPlan:
        """Build verification plan from requested outputs."""
        verifiable = list(request.requested_outputs)
        return VerificationPlan(
            verifiable_claims=verifiable,
            required_operators=context.available_operators,
            required_data=["mock_local_xy_m"],
        )

    def run_precheck(
        self, precheck_request: LowAltPrecheckRequest
    ) -> LowAltPrecheckResult:
        """Execute the full mock low-altitude site precheck."""
        result = LowAltPrecheckResult(request_id=precheck_request.request_id)

        for site in precheck_request.candidate_sites:
            for sensitive in precheck_request.sensitive_sites:
                check = check_sensitive_site_distance(site, sensitive)
                self._categorize(check, result)

        for site in precheck_request.candidate_sites:
            for zone in precheck_request.restricted_zones:
                check = check_site_in_restricted_zone(site, zone)
                self._categorize(check, result)

        for route in precheck_request.initial_routes:
            for zone in precheck_request.restricted_zones:
                check = check_route_restricted_zone_conflict(route, zone)
                self._categorize(check, result)

        if precheck_request.flight_altitude_band:
            for obstacle in precheck_request.obstacles:
                check = check_obstacle_altitude_conflict(
                    obstacle, precheck_request.flight_altitude_band
                )
                self._categorize(check, result)

        for fw in precheck_request.flight_time_windows:
            for rw in precheck_request.restriction_time_windows:
                check = check_time_window_conflict(fw, rw)
                self._categorize(check, result)

        gaps = identify_data_gaps(precheck_request)
        result.planned_data_gaps = gaps
        no_checks = not result.verified_items and not result.contradicted_items and not result.review_items
        if gaps and no_checks:
            result.review_items.append({
                "name": "data_gaps",
                "status": "need_review",
                "detail": f"Missing data: {', '.join(gaps)}",
            })

        result.overall_status = self._compute_overall(result)

        result.summary = (
            f"LowAlt mock site precheck for '{precheck_request.request_id}': "
            f"{len(result.risk_items)} risk(s), "
            f"{len(result.verified_items)} verified, "
            f"{len(result.contradicted_items)} contradicted, "
            f"{len(result.review_items)} need review, "
            f"{len(result.planned_data_gaps)} data gaps. "
            f"{result.disclaimer}"
        )

        return result

    @staticmethod
    def _categorize(check: dict, result: LowAltPrecheckResult):
        """Route a check result to the appropriate list."""
        status = check.get("status", "need_review")
        if status == "contradicted" and check.get("risk", False):
            result.risk_items.append(check)
            result.contradicted_items.append(check)
        elif status == "contradicted":
            result.contradicted_items.append(check)
        elif status == "verified":
            result.verified_items.append(check)
        else:
            result.review_items.append(check)

    @staticmethod
    def _compute_overall(result: LowAltPrecheckResult) -> str:
        """Compute overall status using Core priority hierarchy."""
        for item in result.review_items:
            if item.get("status") == "invalid_operator":
                return "invalid_operator"
            if item.get("status") == "invalid_reference":
                return "invalid_reference"
        if result.contradicted_items:
            return "contradicted"
        if result.review_items:
            return "need_review"
        return "verified"
