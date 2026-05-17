from __future__ import annotations

from dataclasses import dataclass, field

from altrasia.event_bus import EventBus
from altrasia.config import Settings
from altrasia.domain.presence import PresenceService
from altrasia.inference.client import LlmClient
from altrasia.inference.queue import GpuResourceQueue
from altrasia.memory.service import MemoryService
from altrasia.orchestrator.engine import Orchestrator
from altrasia.operator_settings import OperatorSettingsStore
from altrasia.orchestrator.idle_scheduler import IdleScheduler
from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.tools.handlers import register_core_tools
from altrasia.tools.registry import ToolRegistry


@dataclass
class AppServices:
    settings: Settings
    store: SqlitePersistence
    memory: MemoryService
    presence: PresenceService
    gpu_queue: GpuResourceQueue
    llm: LlmClient
    tools: ToolRegistry
    orchestrator: Orchestrator
    operator_settings: OperatorSettingsStore
    idle_scheduler: IdleScheduler | None = None
    event_bus: EventBus = field(default_factory=EventBus)
    streams: dict = field(default_factory=dict)
    paused_worlds: set[str] = field(default_factory=set)

    @classmethod
    def create(cls, settings: Settings | None = None) -> "AppServices":
        settings = settings or Settings()
        store = SqlitePersistence(settings.sqlite_path)
        store.migrate()
        memory = MemoryService(store)
        presence = PresenceService(store)
        gpu = GpuResourceQueue()
        llm = LlmClient(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock=settings.mock_llm,
        )
        tools = ToolRegistry()
        op_path = settings.data_dir / "config.yaml"
        operator_settings = OperatorSettingsStore(op_path)
        svc = cls(
            settings=settings,
            store=store,
            memory=memory,
            presence=presence,
            gpu_queue=gpu,
            llm=llm,
            tools=tools,
            orchestrator=None,  # type: ignore
            operator_settings=operator_settings,
        )
        register_core_tools(tools, svc)
        svc.orchestrator = Orchestrator(svc)
        svc.idle_scheduler = IdleScheduler(svc)
        return svc
