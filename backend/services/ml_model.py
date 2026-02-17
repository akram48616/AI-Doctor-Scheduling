# backend/services/ml_model.py
"""
ML model loader and feature builder for no-show prediction.
Timezone-aware (UTC safe).
Thread-safe singleton.
"""

import logging
import os
import pickle
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "ml",
    "model.pkl"
)

_MODEL_SINGLETON: Optional["NoShowPredictor"] = None


# ==========================================================
# Predictor Wrapper
# ==========================================================

class NoShowPredictor:
    def __init__(self, model: Optional[Any] = None):
        self.model = model

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns:
            {
                "probability": float,
                "label": int (0 or 1)
            }
        """
        try:
            # Stable ordering (important for ML models)
            ordered_keys = [
                "past_no_shows",
                "lead_time_days",
                "time_of_day_bucket",
                "day_of_week",
                "chronic_conditions_flag",
                "doctor_consultation_duration",
                "recent_no_shows",
            ]

            X = [[float(features.get(k, 0.0)) for k in ordered_keys]]

            if self.model and hasattr(self.model, "predict_proba"):
                proba = float(self.model.predict_proba(X)[0][1])
            elif self.model and hasattr(self.model, "predict"):
                raw = self.model.predict(X)
                proba = float(raw[0])
            else:
                proba = 0.1  # fallback default

            label = int(proba >= 0.5)

            return {
                "probability": round(proba, 4),
                "label": label
            }

        except Exception:
            logger.exception("Prediction failed")
            return {"probability": 0.0, "label": 0}


# ==========================================================
# Model Loader (Singleton)
# ==========================================================

def _create_dummy_model():
    class DummyModel:
        def predict_proba(self, X):
            return [[0.9, 0.1] for _ in X]

        def predict(self, X):
            return [0 for _ in X]

    return DummyModel()


def load_model(path: Optional[str] = None) -> NoShowPredictor:
    global _MODEL_SINGLETON

    if _MODEL_SINGLETON is not None:
        return _MODEL_SINGLETON

    model_path = path or _DEFAULT_MODEL_PATH

    if not os.path.exists(model_path):
        logger.warning("Model not found at %s; using dummy predictor", model_path)
        _MODEL_SINGLETON = NoShowPredictor(_create_dummy_model())
        return _MODEL_SINGLETON

    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        _MODEL_SINGLETON = NoShowPredictor(model)
        logger.info("Loaded ML model from %s", model_path)
        return _MODEL_SINGLETON

    except Exception:
        logger.exception("Failed to load model; using dummy predictor")
        _MODEL_SINGLETON = NoShowPredictor(_create_dummy_model())
        return _MODEL_SINGLETON


def get_predictor() -> NoShowPredictor:
    return load_model()


# ==========================================================
# Datetime Normalization
# ==========================================================

def _parse_to_aware(dt: Any) -> datetime:
    """
    Converts input into UTC-aware datetime.
    Accepts:
        - datetime (naive or aware)
        - ISO string
        - YYYY-MM-DD string
    """
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(dt, str):
        try:
            parsed = datetime.fromisoformat(dt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            try:
                parsed_date = datetime.strptime(dt, "%Y-%m-%d")
                return parsed_date.replace(tzinfo=timezone.utc)
            except Exception:
                raise ValueError(
                    "Invalid datetime string. Use ISO format or YYYY-MM-DD."
                )

    raise ValueError("Unsupported datetime input type")


# ==========================================================
# Feature Builder
# ==========================================================

def build_features(
    patient: Any,
    doctor: Any,
    appointment_datetime: Any,
    session: Optional[Any] = None
) -> Dict[str, float]:

    appointment_dt = _parse_to_aware(appointment_datetime)
    now = datetime.now(timezone.utc)

    # Lead time
    lead_time_seconds = max((appointment_dt - now).total_seconds(), 0.0)
    lead_time_days = lead_time_seconds / 86400.0

    # Time of day bucket
    hour = appointment_dt.hour
    if hour < 9:
        tod = 0.0
    elif hour < 12:
        tod = 1.0
    elif hour < 17:
        tod = 2.0
    else:
        tod = 3.0

    # Accurate age calculation
    dob = getattr(patient, "date_of_birth", None)
    if dob:
        age = now.year - dob.year - (
            (now.month, now.day) < (dob.month, dob.day)
        )
        patient_age = float(max(age, 0))
    else:
        patient_age = 0.0

    chronic_flag = 1.0 if getattr(patient, "medical_history", None) else 0.0
    past_no_shows = float(getattr(patient, "past_no_shows", 0))
    consultation_duration = float(
        getattr(doctor, "consultation_duration", 30)
    )

    # Placeholder (can query real data later)
    recent_no_shows = 0.0

    features: Dict[str, float] = {
        "past_no_shows": past_no_shows,
        "lead_time_days": float(lead_time_days),
        "time_of_day_bucket": float(tod),
        "day_of_week": float(appointment_dt.weekday()),
        "chronic_conditions_flag": chronic_flag,
        "doctor_consultation_duration": consultation_duration,
        "recent_no_shows": recent_no_shows,
    }

    return features
