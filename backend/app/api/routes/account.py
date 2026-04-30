from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.saju import AccountMeResponse, AccountOrderResponse, AccountReadingResponse
from app.services.reading_repository import ReadingRepository, get_reading_repository
from app.services.supabase_auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api/account", tags=["account"])


@router.get("/me", response_model=AccountMeResponse)
async def account_me(
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
) -> AccountMeResponse:
    profile = await repo.get_profile(current_user.id)
    if profile.email is None:
        return profile.model_copy(update={"email": current_user.email})
    return profile


@router.get("/orders", response_model=list[AccountOrderResponse])
async def account_orders(
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
) -> list[AccountOrderResponse]:
    return await repo.list_orders(current_user.id)


@router.get("/readings", response_model=list[AccountReadingResponse])
async def account_readings(
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
) -> list[AccountReadingResponse]:
    return await repo.list_readings(current_user.id)
