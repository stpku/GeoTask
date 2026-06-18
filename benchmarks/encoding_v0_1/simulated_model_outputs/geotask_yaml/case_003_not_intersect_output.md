measurements:
  - name: takeoff_to_school_distance
    value: 144.22
    unit: meter
    verified_by: distance_2d
  - name: route_intersects_zone
    value: false
    unit: null
    verified_by: line_intersects_rect

conclusion:
  summary: "takeoff_to_school_distance=144.22 meter; route_intersects_zone=false"
  external_data_used: false

verified_by:
  - operation: distance_2d
    result: "144.22 meter"
  - operation: line_intersects_rect
    result: "false"
