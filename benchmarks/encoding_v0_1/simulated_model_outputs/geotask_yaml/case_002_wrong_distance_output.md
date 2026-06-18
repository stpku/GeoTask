measurements:
  - name: takeoff_to_school_distance
    value: 150.0
    unit: meter
    verified_by: distance_2d
  - name: route_intersects_zone
    value: true
    unit: null
    verified_by: line_intersects_rect

conclusion:
  summary: "takeoff_to_school_distance=150.0 meter; route_intersects_zone=true"
  external_data_used: false

verified_by:
  - operation: distance_2d
    result: "150.0 meter"
  - operation: line_intersects_rect
    result: "true"
