from copy import deepcopy


SCORING_PROFILES = {
    "defense": {
        "key": "defense",
        "label": "答辩模式",
        "weights": {
            "language": 35,
            "posture": 25,
            "content": 25,
            "qa": 15,
        },
    },
    "interview": {
        "key": "interview",
        "label": "面试模式",
        "weights": {
            "language": 40,
            "posture": 20,
            "content": 10,
            "qa": 30,
        },
    },
}

DEFAULT_SCORING_PROFILE = "defense"


def get_scoring_profile(profile_key: str | None = None) -> dict:
    key = (profile_key or DEFAULT_SCORING_PROFILE).strip().lower()
    profile = SCORING_PROFILES.get(key) or SCORING_PROFILES[DEFAULT_SCORING_PROFILE]
    return deepcopy(profile)
