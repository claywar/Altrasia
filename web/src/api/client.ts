const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err?.error?.message ?? r.statusText);
  }
  return r.json() as Promise<T>;
}

export type World = {
  worldId: string;
  name: string;
  activeSceneId: string;
  paused?: boolean;
  policy?: WorldPolicy;
};

export type WorldPolicy = {
  requireWebToolApproval?: boolean;
  auditWebTools?: boolean;
  pauseCommissionsDuringPersonaDialogue?: boolean;
  mandatoryRecallBlocking?: boolean;
  maxContinueDepth?: number;
  citeProvenanceInPrompt?: boolean;
  commonsAccessIds?: string[];
};

export type EvidenceRecord = {
  evidenceId: string;
  locusKey: string;
  pool: string;
  ownerId: string;
  sourceKind: string;
  sourceRef: string;
  retrievedAt: string;
  commissionId?: string | null;
};

export type Scene = {
  sceneId: string;
  worldId: string;
  locationName: string;
  locationDescription: string;
  presentJson: string;
  exitsJson: string;
  activityJson?: string | null;
};

export type DebateActivity = {
  kind: "debate";
  phase: string;
  speakingOrder: string[];
  currentIndex: number;
};

export type LayoutDraft = {
  layoutDraftId: string;
  worldId: string;
  operatorBrief: string;
  scope: string;
  proposed: { nodes?: Array<{ sceneId: string; mapPosition: { x: number; y: number } }> } | null;
  status: string;
  errorMessage?: string | null;
};

export type Message = {
  messageId: string;
  role: string;
  characterId: string | null;
  outputText: string;
  streamStatus: string;
  metaJson: string;
  generationJobId?: string | null;
  perceivedByPersona?: boolean;
};

export type GenerationJob = {
  jobId: string;
  characterId: string;
  trigger: string;
  continueDepth?: number;
  selectionRationaleJson?: string;
  status?: string;
};

export type QueueSnapshot = {
  busy: boolean;
  depth: number;
  estimatedWaitMs?: number;
  currentJob?: GenerationJob | null;
  gpu?: {
    busy: boolean;
    currentLease?: { kind: string; jobId: string } | null;
  };
};

export type OperatorSettings = {
  heartbeat: { enabled: boolean; intervalSeconds: number };
  lastHeartbeatAt: string | null;
};

export type CharacterDefinition = {
  persona: string;
  instructions: string;
  focusTags?: string[];
  speechWeight?: number;
  modelProfile?: string;
};

export type Commission = {
  commissionId: string;
  worldId: string;
  assigneeCharacterId: string;
  targetSceneId: string;
  brief: string;
  status: string;
  deliverablePolicy: string;
  deliverableLocusPrefix?: string | null;
  deliverableLocusKeys: string[];
  forceCompleteReason?: string | null;
  allowedTools?: string[];
  createdAt: string;
  updatedAt: string;
};

export function parseDebateActivity(scene: Scene | null): DebateActivity | null {
  if (!scene?.activityJson) return null;
  try {
    const a = JSON.parse(scene.activityJson) as DebateActivity;
    return a?.kind === "debate" ? a : null;
  } catch {
    return null;
  }
}

export type CharacterDraft = {
  draftId: string;
  status: string;
  operatorBrief: string;
  definitionJson: CharacterDefinition | null;
  errorMessage?: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ObserverDigest = {
  worldId: string;
  worldName?: string;
  activeSceneId: string;
  paused: boolean;
  summary: string;
  scenes: Array<{
    sceneId: string;
    locationName: string;
    presentCharacterIds: string[];
    presentCount: number;
  }>;
  pendingSignals: Array<{
    signalId: string;
    kind: string;
    sourceSceneId: string;
    targetSceneId: string;
    status: string;
  }>;
  activeChannels: PhoneChannel[];
  commissions?: Commission[];
  debates?: Array<{
    sceneId: string;
    locationName: string;
    phase: string;
    speakingOrder: string[];
  }>;
  pendingApprovals?: Approval[];
};

export type Approval = {
  approvalId: string;
  worldId: string;
  toolName: string;
  params: Record<string, unknown>;
  state: string;
  createdAt: string;
};

export type SpatialGraph = {
  activeSceneId: string;
  nodes: Array<{
    sceneId: string;
    locationName: string;
    isActive: boolean;
    layout: { x: number; y: number };
    presentCount: number;
  }>;
  edges: Array<{
    exitId: string;
    sourceSceneId: string;
    targetSceneId: string;
    label: string;
  }>;
};

export const api = {
  listWorlds: () => request<World[]>("/worlds"),
  loadDemo: () =>
    request<World>("/worlds", {
      method: "POST",
      body: JSON.stringify({ fixtureId: "demo-spatial-v1" }),
    }),
  createBlankWorld: (name: string) =>
    request<World>("/worlds", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  geography: (worldId: string) =>
    request<{
      layoutDesignMode: boolean;
      geographyLockedAt: string | null;
      sceneCount: number;
    }>(`/worlds/${worldId}/geography`),
  lockGeography: (worldId: string) =>
    request<{ layoutDesignMode: boolean; geographyLockedAt: string | null }>(
      `/worlds/${worldId}/geography/lock`,
      { method: "POST" }
    ),
  createScene: (
    worldId: string,
    body: {
      locationName: string;
      locationDescription?: string;
      connectFromSceneId?: string;
      exitLabel?: string;
      reverseExitLabel?: string;
    }
  ) => request<Scene>(`/worlds/${worldId}/scenes`, { method: "POST", body: JSON.stringify(body) }),
  deleteScene: (worldId: string, sceneId: string) =>
    request<{ deleted: string }>(`/worlds/${worldId}/scenes/${sceneId}`, { method: "DELETE" }),
  patchScene: (
    worldId: string,
    sceneId: string,
    body: { locationName?: string; locationDescription?: string }
  ) =>
    request<Scene>(`/worlds/${worldId}/scenes/${sceneId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  listCommissions: (worldId: string) =>
    request<Commission[]>(`/worlds/${worldId}/commissions`),
  createCommission: (
    worldId: string,
    body: {
      assigneeCharacterId: string;
      targetSceneId: string;
      brief: string;
      deliverablePolicy?: string;
      allowedTools?: string[];
    }
  ) =>
    request<Commission>(`/worlds/${worldId}/commissions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createLayoutDraft: (worldId: string, body: { brief: string; scope?: string }) =>
    request<LayoutDraft>(`/worlds/${worldId}/layout-drafts`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getLayoutDraft: (worldId: string, draftId: string) =>
    request<LayoutDraft>(`/worlds/${worldId}/layout-drafts/${draftId}`),
  commitLayoutDraft: (worldId: string, draftId: string) =>
    request<{ layoutDraftId: string; applied: string[]; conflicts: unknown[] }>(
      `/worlds/${worldId}/layout-drafts/${draftId}/commit`,
      { method: "POST" }
    ),
  getDebate: (worldId: string, sceneId: string) =>
    request<{ activity: DebateActivity | null }>(`/worlds/${worldId}/scenes/${sceneId}/debate`),
  startDebate: (
    worldId: string,
    sceneId: string,
    body: { speakingOrder: string[]; phase?: string }
  ) =>
    request<{ activity: DebateActivity; generationJob?: { jobId: string } }>(
      `/worlds/${worldId}/scenes/${sceneId}/debate`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  advanceDebateSpeaker: (worldId: string, sceneId: string) =>
    request<{ activity: DebateActivity; generationJob?: { jobId: string } }>(
      `/worlds/${worldId}/scenes/${sceneId}/debate/advance-speaker`,
      { method: "POST" }
    ),
  advanceDebatePhase: (worldId: string, sceneId: string) =>
    request<{ activity: DebateActivity; generationJob?: { jobId: string } }>(
      `/worlds/${worldId}/scenes/${sceneId}/debate/advance-phase`,
      { method: "POST" }
    ),
  endDebate: (worldId: string, sceneId: string) =>
    request<{ sceneId: string; activity: null }>(
      `/worlds/${worldId}/scenes/${sceneId}/debate`,
      { method: "DELETE" }
    ),
  listApprovals: (worldId: string, state = "pending") =>
    request<Approval[]>(`/worlds/${worldId}/approvals?state=${state}`),
  approveApproval: (worldId: string, approvalId: string) =>
    request<Approval>(`/worlds/${worldId}/approvals/${approvalId}/approve`, {
      method: "POST",
    }),
  denyApproval: (worldId: string, approvalId: string) =>
    request<Approval>(`/worlds/${worldId}/approvals/${approvalId}/deny`, { method: "POST" }),
  patchCommission: (
    worldId: string,
    commissionId: string,
    body: {
      status?: string;
      deliverableLocusKeys?: string[];
      forceCompleteReason?: string;
    }
  ) =>
    request<Commission>(`/worlds/${worldId}/commissions/${commissionId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  startCommission: (worldId: string, commissionId: string) =>
    request<{ commissionId: string; generationJob?: { jobId: string } }>(
      `/worlds/${worldId}/commissions/${commissionId}/start`,
      { method: "POST" }
    ),
  exportPackage: async (worldId: string): Promise<Blob> => {
    const r = await fetch(`${BASE}/worlds/${worldId}/package/export`);
    if (!r.ok) throw new Error(r.statusText);
    return r.blob();
  },
  importPackage: async (file: File): Promise<World> => {
    const form = new FormData();
    form.append("file", file);
    const r = await fetch(`${BASE}/worlds/import`, { method: "POST", body: form });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err?.detail ?? r.statusText);
    }
    return r.json() as Promise<World>;
  },
  getWorld: (id: string) => request<World>(`/worlds/${id}`),
  patchWorld: (id: string, body: Partial<World>) =>
    request<World>(`/worlds/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  getWorldPolicy: (worldId: string) => request<WorldPolicy>(`/worlds/${worldId}/policy`),
  patchWorldPolicy: (worldId: string, body: Partial<WorldPolicy>) =>
    request<WorldPolicy>(`/worlds/${worldId}/policy`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  characterEvidence: (worldId: string, characterId: string, locusKey?: string) =>
    request<EvidenceRecord[]>(
      `/worlds/${worldId}/characters/${characterId}/evidence${
        locusKey ? `?locusKey=${encodeURIComponent(locusKey)}` : ""
      }`
    ),
  setBriefing: (
    worldId: string,
    sceneId: string,
    body: { text: string; fixtureKey?: string }
  ) =>
    request<{ fixtureKey: string; locusKey: string; sceneId: string }>(
      `/worlds/${worldId}/scenes/${sceneId}/briefing`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  listScenes: (worldId: string) => request<Scene[]>(`/worlds/${worldId}/scenes`),
  listCharacters: (worldId: string) =>
    request<
      Array<{
        characterId: string;
        displayName: string;
        definition?: CharacterDefinition;
        muted?: boolean;
        disabled?: boolean;
      }>
    >(`/worlds/${worldId}/characters`),
  getScene: (worldId: string, sceneId: string) =>
    request<Scene>(`/worlds/${worldId}/scenes/${sceneId}`),
  listMessages: (worldId: string, sceneId: string) =>
    request<Message[]>(`/worlds/${worldId}/scenes/${sceneId}/messages`),
  sendMessage: (
    worldId: string,
    sceneId: string,
    body: { text: string; scope: string; participants?: string[]; channelId?: string }
  ) =>
    request<{ messageId: string; generationJob?: { jobId: string } }>(
      `/worlds/${worldId}/scenes/${sceneId}/messages`,
      { method: "POST", body: JSON.stringify({ ...body, asPersona: true }) }
    ),
  roster: (worldId: string) =>
    request<{
      atLocation: Array<{
        characterId: string;
        displayName: string;
        sceneId: string;
        locationName?: string;
      }>;
      elsewhere: Array<{
        characterId: string;
        displayName: string;
        locationName: string | null;
        sceneId?: string;
      }>;
      unplaced?: Array<{ characterId: string; displayName: string }>;
    }>(`/worlds/${worldId}/roster`),
  summonPresence: (
    worldId: string,
    body: { characterIds: string[]; targetSceneId: string }
  ) =>
    request<{ ok: boolean; targetSceneId: string }>(`/worlds/${worldId}/presence/summon`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  leavePresence: (worldId: string, sceneId: string, characterId: string) =>
    request(`/worlds/${worldId}/scenes/${sceneId}/presence/leave`, {
      method: "POST",
      body: JSON.stringify({ characterId }),
    }),
  spatialGraph: (worldId: string) => request<SpatialGraph>(`/worlds/${worldId}/spatial-graph`),
  queue: (worldId: string) => request<QueueSnapshot>(`/worlds/${worldId}/queue`),
  getGeneration: (worldId: string, jobId: string) =>
    request<GenerationJob>(`/worlds/${worldId}/generations/${jobId}`),
  characterMind: (worldId: string, characterId: string) =>
    request<Array<{ locusKey: string; value: string; updatedAt?: string }>>(
      `/worlds/${worldId}/characters/${characterId}/mind`
    ),
  characterDiary: (worldId: string, characterId: string) =>
    request<Array<{ text: string; createdAt: string; segmentId?: string }>>(
      `/worlds/${worldId}/characters/${characterId}/diary`
    ),
  dismissSignal: (worldId: string, signalId: string) =>
    request(`/worlds/${worldId}/signals/${signalId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "dismissed" }),
    }),
  signals: (worldId: string) =>
    request<
      Array<{
        signalId: string;
        targetSceneId: string;
        sourceSceneId: string;
        kind: string;
        status?: string;
      }>
    >(`/worlds/${worldId}/signals`),
  knock: (
    worldId: string,
    body: { sourceSceneId: string; targetSceneId: string; kind?: string }
  ) =>
    request(`/worlds/${worldId}/signals`, { method: "POST", body: JSON.stringify(body) }),
  joinPresence: (worldId: string, sceneId: string, characterId: string) =>
    request(`/worlds/${worldId}/scenes/${sceneId}/presence/join`, {
      method: "POST",
      body: JSON.stringify({ characterId }),
    }),
  metaMessages: (worldId: string) =>
    request<Message[]>(`/worlds/${worldId}/observer/meta-messages`),
  observerDigest: (worldId: string) =>
    request<ObserverDigest>(`/worlds/${worldId}/observer/digest`),
  createCharacterDraft: (brief: string) =>
    request<CharacterDraft>("/characters/draft", {
      method: "POST",
      body: JSON.stringify({ brief }),
    }),
  getCharacterDraft: (draftId: string) =>
    request<CharacterDraft>(`/characters/draft/${draftId}`),
  discardCharacterDraft: (draftId: string) =>
    request<{ draftId: string; status: string }>(`/characters/draft/${draftId}`, {
      method: "DELETE",
    }),
  approveCharacter: (body: {
    draftId: string;
    worldId?: string;
    displayName?: string;
    definitionJson?: CharacterDefinition;
  }) =>
    request<{ characterId: string; draftId: string; displayName: string }>("/characters", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  addWorldMember: (worldId: string, characterId: string) =>
    request<{ worldId: string; characterId: string }>(`/worlds/${worldId}/members`, {
      method: "POST",
      body: JSON.stringify({ characterId }),
    }),
  postMeta: (worldId: string, text: string) =>
    request(`/worlds/${worldId}/observer/meta-messages`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  cancelJob: (jobId: string) =>
    request(`/inference/queue/${jobId}`, { method: "DELETE" }),
  operatorSettings: () => request<OperatorSettings>("/operator/settings"),
  patchOperatorSettings: (body: { heartbeat?: { enabled?: boolean; intervalSeconds?: number } }) =>
    request<OperatorSettings>("/operator/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  pauseWorld: (worldId: string) =>
    request(`/worlds/${worldId}/pause`, { method: "POST" }),
  resumeWorld: (worldId: string) =>
    request(`/worlds/${worldId}/resume`, { method: "POST" }),
  listChannels: (worldId: string) => request<PhoneChannel[]>(`/worlds/${worldId}/channels`),
  createPhoneChannel: (
    worldId: string,
    body: {
      sceneIdA: string;
      characterIdA: string;
      sceneIdB: string;
      characterIdB: string;
    }
  ) => request<PhoneChannel>(`/worlds/${worldId}/channels`, { method: "POST", body: JSON.stringify(body) }),
  setSpeakerphone: (worldId: string, channelId: string, sceneId: string, speakerphone: boolean) =>
    request<PhoneChannel>(
      `/worlds/${worldId}/channels/${channelId}/endpoints/${sceneId}`,
      { method: "PATCH", body: JSON.stringify({ speakerphone }) }
    ),
  endPhoneChannel: (worldId: string, channelId: string) =>
    request(`/worlds/${worldId}/channels/${channelId}/end`, { method: "POST" }),
  answerSignal: (
    worldId: string,
    signalId: string,
    body: { characterId: string; targetSceneId?: string }
  ) =>
    request(`/worlds/${worldId}/signals/${signalId}/answer`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export type PhoneChannel = {
  channelId: string;
  worldId: string;
  active: boolean;
  participants: string[];
  endpoints: Array<{
    sceneId: string;
    participantIds: string[];
    speakerphone: boolean;
  }>;
};

export function connectWorldEvents(
  worldId: string,
  onEvent: (payload: { event: string; eventSeq: number; data: unknown }) => void
): () => void {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const ws = new WebSocket(`${proto}//${host}/api/v1/worlds/${worldId}/events`);
  ws.onmessage = (ev) => {
    try {
      onEvent(JSON.parse(ev.data));
    } catch {
      /* ignore */
    }
  };
  return () => ws.close();
}

export function streamGeneration(
  worldId: string,
  jobId: string,
  onEvent: (event: string, data: unknown) => void
): () => void {
  const es = new EventSource(`${BASE}/worlds/${worldId}/generations/${jobId}/stream`);
  const handler = (type: string) => (e: MessageEvent) => {
    try {
      onEvent(type, JSON.parse(e.data));
    } catch {
      onEvent(type, e.data);
    }
  };
  es.addEventListener("generation.token", handler("generation.token"));
  es.addEventListener("generation.done", handler("generation.done"));
  es.addEventListener("generation.error", handler("generation.error"));
  es.onerror = () => es.close();
  return () => es.close();
}
