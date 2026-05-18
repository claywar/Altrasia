from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from altrasia.event_bus import EventBus
from altrasia.config import Settings
from altrasia.communication.phone import PhoneService
from altrasia.domain.presence import PresenceService
from altrasia.inference.client import LlmClient
from altrasia.inference.queue import GpuResourceQueue
from altrasia.memory.embeddings import EmbeddingService
from altrasia.memory.service import MemoryService
from altrasia.orchestrator.engine import Orchestrator
from altrasia.operator_settings import OperatorSettingsStore
from altrasia.orchestrator.idle_scheduler import IdleScheduler
from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.plugins.loader import PluginHost, load_plugins
from altrasia.tools.fs_agent import FsAgent
from altrasia.tools.handlers import register_core_tools
from altrasia.tools.registry import ToolRegistry


@dataclass
class AppServices:
    settings: Settings
    store: SqlitePersistence
    memory: MemoryService
    presence: PresenceService
    phone: PhoneService
    gpu_queue: GpuResourceQueue
    llm: LlmClient
    tools: ToolRegistry
    orchestrator: Orchestrator
    operator_settings: OperatorSettingsStore
    embeddings: EmbeddingService
    plugins: PluginHost
    idle_scheduler: IdleScheduler | None = None
    event_bus: EventBus = field(default_factory=EventBus)
    streams: dict = field(default_factory=dict)
    paused_worlds: set[str] = field(default_factory=set)
    _fs_agents: dict[str, FsAgent] = field(default_factory=dict)

    def fs_for_world(self, world_id: str) -> FsAgent:
        if world_id not in self._fs_agents:
            root = self.settings.data_dir / "worlds" / world_id / "files"
            self._fs_agents[world_id] = FsAgent(root)
        return self._fs_agents[world_id]

    @classmethod
    def create(cls, settings: Settings | None = None) -> "AppServices":
        settings = settings or Settings()
        store = SqlitePersistence(settings.sqlite_path)
        store.migrate()
        memory = MemoryService(store, hybrid_search_enabled=bool(settings.embed_base_url))
        presence = PresenceService(store)
        phone = PhoneService(store)
        gpu = GpuResourceQueue(max_depth=settings.gpu_max_depth)
        llm = LlmClient(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock=settings.mock_llm,
        )
        tools = ToolRegistry()
        op_path = settings.data_dir / "config.yaml"
        operator_settings = OperatorSettingsStore(op_path)
        plugins = PluginHost()
        svc = cls(
            settings=settings,
            store=store,
            memory=memory,
            presence=presence,
            phone=phone,
            gpu_queue=gpu,
            llm=llm,
            tools=tools,
            orchestrator=None,  # type: ignore
            operator_settings=operator_settings,
            embeddings=EmbeddingService(None),  # type: ignore
            plugins=plugins,
        )
        svc.embeddings = EmbeddingService(svc)
        register_core_tools(tools, svc)
        load_plugins(plugins, tools, svc)
        svc.orchestrator = Orchestrator(svc)
        svc.idle_scheduler = IdleScheduler(svc)
        return svc
