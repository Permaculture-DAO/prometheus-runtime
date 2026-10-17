"""Predictability Boundary endpoint: authenticated, SHADOW-only, opt-in."""
from fastapi import APIRouter, Depends, HTTPException
from .predictability import PredictabilityInput, evaluate_predictability
from .security import require_write_key
from .settings import Settings


def build_predictability_router(settings: Settings) -> APIRouter:
    router = APIRouter(tags=["shadow-predictability"])

    @router.post("/shadow/predictability/evaluate", dependencies=[Depends(require_write_key(settings))])
    def evaluate(payload: PredictabilityInput):
        if not settings.predictability_shadow_enabled:
            raise HTTPException(status_code=423, detail="predictability shadow feature disabled")
        return evaluate_predictability(payload)

    return router
