ROLE_CLIENT = "client"
ROLE_TRAINER = "trainer"
ROLE_ADMIN = "admin"

APP_ROLES = {ROLE_CLIENT, ROLE_TRAINER}
ALL_ROLES = {ROLE_CLIENT, ROLE_TRAINER, ROLE_ADMIN}

AUD_APP = "app"
AUD_ADMIN = "admin"

ALLOWED_GENDERS = {"male", "female", "other"}
DEVICE_PLATFORMS = {"ios", "android", "web"}
SOCIAL_PROVIDERS = {"google", "apple", "telegram"}

FREE_CLIENT_LIMIT = 5

CLIENT_STATUSES = {"new", "permanent", "paused", "archived"}

CLIENT_SORT = {
    "newest": "tc.created_at DESC",
    "oldest": "tc.created_at ASC",
    "alpha": "u.last_name ASC, u.first_name ASC",
    "male_first": "u.gender ASC NULLS LAST, u.last_name ASC",
    "female_first": "u.gender DESC NULLS LAST, u.last_name ASC",
}

TRAINER_SORT = {
    "rating": "COALESCE(tp.rating_avg, 0) DESC, u.id DESC",
    "clients": "clients_count DESC, u.id DESC",
    "newest": "u.created_at DESC",
}

REQUEST_STATUSES = {"pending", "accepted", "rejected"}

MEASUREMENT_METRICS = {
    "weight_kg",
    "body_fat_pct",
    "muscle_mass_kg",
    "water_pct",
    "chest_cm",
    "back_cm",
    "waist_cm",
    "hips_cm",
    "thigh_cm",
    "calf_cm",
    "neck_cm",
    "shoulders_cm",
    "arm_cm",
    "arm_left_cm",
    "arm_right_cm",
    "forearm_cm",
}

SESSION_SORT = {
    "newest": "s.created_at DESC",
    "oldest": "s.created_at ASC",
    "duration_asc": "s.duration_sec ASC NULLS LAST",
    "duration_desc": "s.duration_sec DESC NULLS LAST",
}
