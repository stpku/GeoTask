"""Demo script for GeoTask mock runtime."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import yaml
from geotask_runtime.contracts import TaskRequest, TaskContext, EncodingType
from geotask_runtime.planner import RuleBasedEncodingPlanner
from geotask_runtime.router import MockModelRouter
from geotask_runtime.domain_pack import GenericSpatialDomainPack
from geotask_runtime.mock_runtime import run_mock_runtime, _build_request_from_yaml


def demo():
    print("=" * 60)
    print("GeoTask Mock Runtime Demo v0.1")
    print("=" * 60)

    yaml_path = os.path.join(os.path.dirname(__file__), '..', 'geotask_core_lite.yaml')
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    print("\n1. Building TaskRequest from YAML...")
    req = _build_request_from_yaml(data)
    print(f"   task_id: {req.task_id}")
    print(f"   objects: {len(req.input_objects)}")
    print(f"   outputs: {len(req.requested_outputs)}")

    print("\n2. Running mock runtime pipeline...")
    result = run_mock_runtime(req, geotask_data=data)

    print(f"\n3. Results:")
    print(f"   Overall Status: {result.overall_status}")
    print(f"   Encoding: {result.used_encoding_plan.encoding_type.value}")
    print(f"   Encoding Reason: {result.used_encoding_plan.reason}")
    print(f"\n   Measurements:")
    for m in result.verification_result.get('measurements', []):
        print(f"     {m['name']} = {m['value']} [{m['status']}]")

    print(f"\n   Pipeline Events: {len(result.runtime_events)}")
    print("\n" + "=" * 60)
    print("Demo complete.")


if __name__ == "__main__":
    demo()
