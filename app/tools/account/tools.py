"""Account domain tools."""

from typing import Any

from langchain_core.tools import tool

DEMO_ACCOUNTS: dict[str, dict[str, Any]] = {
    "default": {
        "email": "customer@example.com",
        "name": "Demo Customer",
        "plan": "premium",
        "mfa_enabled": True,
    }
}


@tool
def get_account_profile(customer_id: str = "default") -> dict[str, Any]:
    """Get account profile for a customer."""
    profile = DEMO_ACCOUNTS.get(customer_id)
    if profile is None:
        return {"error": "Account not found", "customer_id": customer_id}
    return profile


@tool
def reset_account_password(customer_id: str = "default") -> dict[str, Any]:
    """Initiate password reset for a customer account."""
    profile = DEMO_ACCOUNTS.get(customer_id)
    if profile is None:
        return {"error": "Account not found", "customer_id": customer_id}
    return {
        "customer_id": customer_id,
        "status": "reset_email_sent",
        "email": profile["email"],
    }


ACCOUNT_TOOLS = [get_account_profile, reset_account_password]
