import secrets
from fastapi import APIRouter
from pydantic import BaseModel

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
async def register(request: RegisterRequest):
    valid_tiers = ["free", "pro", "enterprise"]
    if request.tier not in valid_tiers:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {valid_tiers}")

    api_key = generate_api_key(request.tier)

    return RegisterResponse(
        api_key=api_key,
        email=request.email,
        tier=request.tier,
        message="API key generated successfully. Keep it safe — it won't be shown again.",
    )
