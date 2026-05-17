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
};

export type Scene = {
  sceneId: string;
  worldId: string;
  locationName: string;
  locationDescription: string;
  presentJson: string;
  exitsJson: string;
};

export type Message = {
  messageId: string;
  role: string;
  characterId: string | null;
  outputText: string;
  streamStatus: string;
  metaJson: string;
  perceivedByPersona?: boolean;
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
  loadDemo: () =>
    request<World>("/worlds", {
      method: "POST",
      body: JSON.stringify({ fixtureId: "demo-spatial-v1" }),
    }),
  getWorld: (id: string) => request<World>(`/worlds/${id}`),
  patchWorld: (id: string, body: Partial<World>) =>
    request<World>(`/worlds/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  listScenes: (worldId: string) => request<Scene[]>(`/worlds/${worldId}/scenes`),
  getScene: (worldId: string, sceneId: string) =>
    request<Scene>(`/worlds/${worldId}/scenes/${sceneId}`),
  listMessages: (worldId: string, sceneId: string) =>
    request<Message[]>(`/worlds/${worldId}/scenes/${sceneId}/messages`),
  sendMessage: (
    worldId: string,
    sceneId: string,
    body: { text: string; scope: string; participants?: string[] }
  ) =>
    request<{ messageId: string; generationJob?: { jobId: string } }>(
      `/worlds/${worldId}/scenes/${sceneId}/messages`,
      { method: "POST", body: JSON.stringify({ ...body, asPersona: true }) }
    ),
  roster: (worldId: string) =>
    request<{
      atLocation: Array<{ characterId: string; displayName: string; sceneId: string }>;
      elsewhere: Array<{ characterId: string; displayName: string; locationName: string | null }>;
    }>(`/worlds/${worldId}/roster`),
  spatialGraph: (worldId: string) => request<SpatialGraph>(`/worlds/${worldId}/spatial-graph`),
  queue: (worldId: string) =>
    request<{ busy: boolean; depth: number; currentJob?: { jobId: string } }>(
      `/worlds/${worldId}/queue`
    ),
  signals: (worldId: string) =>
    request<
      Array<{
        signalId: string;
        targetSceneId: string;
        sourceSceneId: string;
        kind: string;
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
  postMeta: (worldId: string, text: string) =>
    request(`/worlds/${worldId}/observer/meta-messages`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  cancelJob: (jobId: string) =>
    request(`/inference/queue/${jobId}`, { method: "DELETE" }),
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
