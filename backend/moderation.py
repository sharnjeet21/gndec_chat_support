# backend/moderation.py
from typing import Tuple, Dict, Any
from functools import lru_cache
import logging
from detoxify import Detoxify

# Tune thresholds per label (industry practice)
THRESHOLDS = {
    "toxicity": 0.85,
    "severe_toxicity": 0.70,
    "threat": 0.70,
    "obscene": 0.70,
    "identity_attack": 0.80,
    "insult": 0.75,
}


@lru_cache(maxsize=1)
def _get_model() -> Detoxify:
    logging.info("Loading Detoxify model (cached)")
    return Detoxify("original")


def check_toxicity(text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Returns (is_toxic, scores)

    FAIL-OPEN: if moderation fails, allow the text.
    """
    if not text or not text.strip():
        return False, {}

    try:
        model = _get_model()
        scores = model.predict(text)

        logging.warning(f"[MODERATION] text={text!r} scores={scores}")

        for label, threshold in THRESHOLDS.items():
            if scores.get(label, 0.0) >= threshold:
                return True, scores

        return False, scores

    except Exception as e:
        logging.error(f"[MODERATION ERROR] {e}", exc_info=True)
        # FAIL OPEN — do not block public chat
        return False, {}
