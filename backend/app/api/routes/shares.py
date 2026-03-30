from __future__ import annotations

from fastapi import APIRouter, status

from app.schemas.share import ShareCreateRequest, SharePayloadRead, ShareResolveRequest, ShareResolveResponse
from app.services.share_service import ShareService

router = APIRouter(prefix="/shares", tags=["shares"])


@router.post("", response_model=SharePayloadRead, status_code=status.HTTP_201_CREATED)
def create_share(payload: ShareCreateRequest) -> SharePayloadRead:
    return ShareService.create_share_payload(payload)


@router.post("/resolve", response_model=ShareResolveResponse, status_code=status.HTTP_200_OK)
def resolve_share(payload: ShareResolveRequest) -> ShareResolveResponse:
    return ShareService.resolve_share_payload(payload)
