from typing import Dict, Tuple
from app.steps_bot.db.models.walk import WalkForm

# Гео и лайв-сообщение
user_coords: Dict[int, Tuple[float, float]] = {}
user_steps: Dict[int, int] = {}
user_msg_id: Dict[int, dict] = {}
user_was_over_speed: Dict[int, bool] = {}
user_walk_finished: Dict[int, bool] = {}

# Дополнительно для коэффициентов/формы/времени
user_walk_multiplier: Dict[int, int] = {}
user_walk_form: Dict[int, WalkForm] = {}
user_walk_started_at: Dict[int, float] = {}
user_temp_c: dict[int, int | None] = {}
user_temp_updated_at: dict[int, float] = {}

# Дневной лимит шагов
user_daily_steps_used: Dict[int, int] = {}
user_daily_steps_date: Dict[int, str] = {}