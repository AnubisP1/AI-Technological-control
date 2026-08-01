from __future__ import annotations

from fastapi import APIRouter

from app.infrastructure.resource_governor import configure as get_resource_limits

router = APIRouter()


@router.get("/health")
def health() -> dict:
    limits = get_resource_limits()
    return {
        "status": "ok",
        "cpu_thread_budget": limits.thread_count,
        "cpu_count_total": limits.cpu_count_total,
    }
