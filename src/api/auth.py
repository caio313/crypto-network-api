import secrets
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.db.session import get_db
from src.models.db.api_keys import ApiKey
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/auth", tags=["auth"])

TIER_PREFIXES = {
    "free": "free",
    "pro": "pro",
    "enterprise": "ent",
}


def generate_api_key(tier: str) -> str:
    prefix = TIER_PREFIXES.get(tier, "free")
    token = secrets.token_urlsafe(24)
    return f"sk-{prefix}-{token}"


class RegisterRequest(BaseModel):
    email: str
    tier: str = "free"


class RegisterResponse(BaseModel):
    api_key: str
    email: str
    tier: str
    message: str


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    valid_tiers = ["free", "pro", "enterprise"]
    if request.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {valid_tiers}")

    result = await db.execute(select(ApiKey).where(ApiKey.email == request.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    api_key = generate_api_key(request.tier)

    new_key = ApiKey(
        key=api_key,
        email=request.email,
        tier=request.tier,
    )
    db.add(new_key)
    await db.commit()

    return RegisterResponse(
        api_key=api_key,
        email=request.email,
        tier=request.tier,
        message="API key generated successfully. Keep it safe — it won't be shown again.",
    )
