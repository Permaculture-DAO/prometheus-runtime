from __future__ import annotations

from dataclasses import dataclass

from .settings import Settings


@dataclass(frozen=True)
class AdapterDescriptor:
    adapter_id: str
    source_system: str
    enabled: bool
    fixture_only: bool
    statement: str = "evaluation, not certification"


def list_ingestion_adapters(settings: Settings) -> list[AdapterDescriptor]:
    return [
        AdapterDescriptor(
            adapter_id="ttn_mock",
            source_system="ttn",
            enabled=settings.s4_ttn_mock_enabled,
            fixture_only=True,
        ),
        AdapterDescriptor(
            adapter_id="manual_mock",
            source_system="manual",
            enabled=settings.s4_manual_mock_enabled,
            fixture_only=True,
        ),
        AdapterDescriptor(
            adapter_id="lab_mock",
            source_system="lab",
            enabled=settings.s4_lab_mock_enabled,
            fixture_only=True,
        ),
    ]


def adapter_by_id(settings: Settings, adapter_id: str) -> AdapterDescriptor | None:
    return next((adapter for adapter in list_ingestion_adapters(settings) if adapter.adapter_id == adapter_id), None)


def ingestion_gate_status(settings: Settings) -> dict:
    adapters = list_ingestion_adapters(settings)
    return {
        "stage": "S4 draft",
        "live_ingestion_admitted": settings.s4_live_ingestion_admitted,
        "ingestion_enabled": settings.s4_ingestion_enabled,
        "production_admitted": settings.production_admitted,
        "statement": settings.runtime_statement,
        "adapters": [
            {
                "adapter_id": adapter.adapter_id,
                "source_system": adapter.source_system,
                "enabled": adapter.enabled,
                "fixture_only": adapter.fixture_only,
                "statement": adapter.statement,
            }
            for adapter in adapters
        ],
    }
