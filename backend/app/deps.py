"""Dependency injection container.

We build a single :class:`Container` during the FastAPI lifespan and expose
it through ``app.state.container``. Request handlers receive collaborators
via ``Depends(...)`` rather than reaching for module-level globals — this
is what makes the engine, retriever, and LLM client trivially mockable in
tests and in future ``/explain`` or ``/compare`` endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from .catalog.loader import load_catalog
from .catalog.models import Assessment
from .config import Settings, get_settings
from .conversation.engine import ConversationEngine
from .llm.gemini import GeminiClient
from .observability.errors import NotReady
from .observability.logging import get_logger
from .retrieval.hybrid import HybridRetriever

log = get_logger(__name__)


@dataclass
class Container:
    settings: Settings
    catalog: list[Assessment]
    retriever: HybridRetriever
    llm: GeminiClient | None
    engine: ConversationEngine

    @property
    def catalog_size(self) -> int:
        return len(self.catalog)


def build_container(settings: Settings | None = None) -> Container:
    """Construct every long-lived collaborator. Called once at startup."""
    settings = settings or get_settings()
    log.info("startup_loading_catalog", extra={"path": str(settings.catalog_file)})
    catalog = load_catalog(settings.catalog_file)
    log.info("startup_building_retriever", extra={"catalog_size": len(catalog)})
    retriever = HybridRetriever(catalog, settings)
    llm: GeminiClient | None = None
    if settings.gemini_api_key:
        try:
            llm = GeminiClient()
            log.info("startup_llm_ready", extra={"model": settings.gemini_model})
        except Exception as exc:  # noqa: BLE001
            log.warning("startup_llm_unavailable", extra={"error": str(exc)})
            llm = None
    else:
        log.info("startup_llm_skipped", extra={"reason": "no_api_key"})
    engine = ConversationEngine(catalog, retriever, settings, llm)
    log.info("startup_complete", extra={"catalog_size": len(catalog)})
    return Container(settings, catalog, retriever, llm, engine)


# ---------- FastAPI dependencies ----------

def get_container(request: Request) -> Container:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise NotReady("Service container has not finished initializing.")
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_engine(container: ContainerDep) -> ConversationEngine:
    return container.engine


def get_settings_dep(container: ContainerDep) -> Settings:
    return container.settings


EngineDep = Annotated[ConversationEngine, Depends(get_engine)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
