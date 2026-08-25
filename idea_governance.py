import os
import hmac
from typing import Dict, Any

VALID_TRANSITIONS = {
    "DISCOVERED": ["RESEARCHED"],
    "RESEARCHED": ["SCORED"],
    "SCORED": ["SHORTLISTED"],
    "SHORTLISTED": ["HUMAN_REVIEW"],
    "HUMAN_REVIEW": ["APPROVED", "REJECTED"],
    "APPROVED": ["PRODUCTION"],
    "PRODUCTION": ["QUALITY_CHECK"],
    "QUALITY_CHECK": ["PUBLISH_READY", "REJECTED"],
    "PUBLISH_READY": ["PUBLISHED"],
    "PUBLISHED": ["MONITORING"],
    "REJECTED": ["DISCOVERED"]
}

HUMAN_MANDATORY_STATES = {"APPROVED", "PUBLISHED"}

def verify_human_authorization_token(provided_key: str) -> bool:
    expected_secret = os.getenv("GOVERNANCE_SECRET") or os.getenv("DOWNLOAD_SECRET")
    if not expected_secret or not provided_key:
        return False
    return hmac.compare_digest(provided_key.strip(), expected_secret.strip())

def validate_state_transition(
    current_state: str,
    target_state: str,
    autonomy_level: int = 2,
    actor: str = "SYSTEM",
    governance_key: str = ""
) -> Dict[str, Any]:
    allowed_targets = VALID_TRANSITIONS.get(current_state, [])
    if target_state not in allowed_targets:
        return {
            "allowed": False,
            "error_code": 400,
            "message": f"Illegal transition from '{current_state}' to '{target_state}'. Allowed: {allowed_targets}"
        }

    if autonomy_level >= 2 and target_state in HUMAN_MANDATORY_STATES:
        if actor != "HUMAN_OPERATOR" or not verify_human_authorization_token(governance_key):
            return {
                "allowed": False,
                "error_code": 403,
                "message": f"Governance Gate Violation: Transition to '{target_state}' requires verified HUMAN_OPERATOR authorization with a valid Governance Key under Autonomy Level {autonomy_level}."
            }

    return {
        "allowed": True,
        "error_code": 200,
        "message": f"Transition from '{current_state}' to '{target_state}' authorized."
    }