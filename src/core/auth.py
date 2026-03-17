import hashlib
import secrets
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.db.api_keys import ApiKey, TierEnum


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256 with a salt.
    In production, you should use a proper secret salt from environment variables.
    For now, we'll use a fixed salt for demonstration.
    """
    # In a real application, use a secret salt from environment variables
    salt = "crypto-network-salt-change-in-production"
    return hashlib.sha256((api_key + salt).encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


async def validate_api_key(
    db: AsyncSession, api_key: str
) -> Tuple[Optional[ApiKey], Optional[str]]:
    """
    Validate an API key by comparing its hash with stored hash.

    Returns:
        Tuple of (ApiKey object, error_message)
        If valid: (ApiKey, None)
        If invalid: (None, error_message)
    """
    if not api_key:
        return None, "API key is required"

    # Hash the provided API key
    hashed_key = hash_api_key(api_key)

    # Look up the API key in the database
    result = await db.execute(select(ApiKey).where(ApiKey.key == hashed_key))
    api_key_record = result.scalar_one_or_none()

    if not api_key_record:
        return None, "Invalid API key"

    # Properly access the column value - use .is_active == False for SQLAlchemy
    if not api_key_record.is_active:  # type: ignore
        return None, "API key is inactive"

    return api_key_record, None


def check_tier_access(
    api_key_record: ApiKey, required_tier: TierEnum
) -> Tuple[bool, Optional[str]]:
    """
    Check if the API key's tier has access to the required tier level.

    Returns:
        Tuple of (has_access, error_message)
    """
    tier_hierarchy = {TierEnum.free: 0, TierEnum.pro: 1, TierEnum.enterprise: 2}

    # Get the actual value from the column
    user_tier_value = api_key_record.tier.value  # This gets the actual enum value
    user_level = tier_hierarchy[TierEnum(user_tier_value)]
    required_level = tier_hierarchy[required_tier]

    if user_level >= required_level:
        return True, None
    else:
        return False, f"Plan required: {required_tier.value.upper()}"


async def increment_request_count(db: AsyncSession, api_key_record: ApiKey):
    """
    Increment the daily request count for an API key.
    In a production system, this would use a proper counter with date reset.
    For simplicity, we're storing as string and incrementing.
    """
    try:
        # Properly access and update the column value
        current_count = int(api_key_record.requests_today)  # Get current value
        # For SQLAlchemy, we need to use the correct attribute assignment
        api_key_record.requests_today = str(current_count + 1)  # Set new value
        await db.commit()
    except (ValueError, AttributeError):
        # If conversion fails, reset to 1
        api_key_record.requests_today = "1"
        await db.commit()
