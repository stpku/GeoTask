Based on the spatial scene provided, here are my calculations:

1. **Distance from site to school**:
   Using the formula distance_2d = sqrt((x1 - x2)^2 + (y1 - y2)^2):
   - site: (0, 0)
   - school: (120, 80)
   - delta_x = 120 - 0 = 120
   - delta_y = 80 - 0 = 80
   - distance = sqrt(120^2 + 80^2) = sqrt(14400 + 6400) = sqrt(20800) ≈ 144.22 meters

2. **Route-zone intersection**:
   The route goes from (-200, 0) to (400, 0), which is a horizontal line along y=0.
   The zone is a rectangle from (250, -100) to (350, 100).
   Since the line y=0 passes through the zone's y-range [-100, 100] and x-range [250, 350],
   the route does intersect the zone. Result: true

Measurements:
- takeoff_to_school_distance: 144.22 meters
- route_intersects_zone: true

Operations used: distance_2d, line_intersects_rect
