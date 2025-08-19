from geopy.distance import geodesic

STEP_LENGTH = 0.75  # метра
MIN_DISTANCE = 5.5
MAX_DISTANCE = 50
MAX_SPEED = 8  # км/ч


def calculate_distance_m(prev: tuple[float, float], curr: tuple[float, float]) -> float:
    return geodesic(prev, curr).meters


def calculate_steps(prev: tuple[float, float], curr: tuple[float, float]) -> int:
    distance = calculate_distance_m(prev, curr)
    if MIN_DISTANCE <= distance <= MAX_DISTANCE:
        return int(distance / STEP_LENGTH)
    return 0


def is_too_fast(prev_coords: tuple[float, float], curr_coords: tuple[float, float], prev_ts: float, curr_ts: float) -> bool:
    delta_t = curr_ts - prev_ts
    if delta_t <= 0:
        return True
    distance = calculate_distance_m(prev_coords, curr_coords)
    speed_kmh = (distance / delta_t) * 3.6
    return speed_kmh > MAX_SPEED
