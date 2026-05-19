import type { SpatialGraph } from "../../api/client";

export type DoorState = "closed" | "unlocked" | "open" | "broken";

export type ExitRow = {
  exitId: string;
  label: string;
  targetSceneId: string;
  direction?: string;
  doorState?: DoorState | string;
  kind?: string;
};

export type ExitKnockAffordance = {
  showKnock: boolean;
  label: string;
  disabled: boolean;
  statusChip?: string;
};

function normalizeDoorState(state?: string): DoorState | undefined {
  if (!state) return undefined;
  const s = state.toLowerCase();
  if (s === "closed" || s === "unlocked" || s === "open" || s === "broken") {
    return s;
  }
  return undefined;
}

function isDoorExit(exit: ExitRow): boolean {
  if (exit.kind === "door") return true;
  return normalizeDoorState(exit.doorState) !== undefined;
}

function statusLabelForDoor(state: DoorState | undefined): string | undefined {
  switch (state) {
    case "open":
      return "Open";
    case "broken":
      return "Broken";
    case "unlocked":
      return "Unlocked";
    case "closed":
      return "Closed";
    default:
      return undefined;
  }
}

/** Merge exit row with spatial-graph edge (doorState, kind). */
export function mergeExitWithGraphEdge(
  exit: ExitRow,
  edges: SpatialGraph["edges"] | undefined,
  activeSceneId: string
): ExitRow {
  if (!edges?.length) return exit;
  const edge = edges.find(
    (e) => e.exitId === exit.exitId && e.sourceSceneId === activeSceneId
  );
  if (!edge) return exit;
  return {
    ...exit,
    doorState: exit.doorState ?? edge.doorState,
    kind: exit.kind ?? edge.kind,
  };
}

/** Knock affordance for ExitList and map inspectors. */
export function exitKnockAffordance(
  exit: ExitRow,
  pendingKnockTargetIds?: Set<string>
): ExitKnockAffordance {
  const doorState = normalizeDoorState(exit.doorState);
  const door = isDoorExit(exit);
  const pending = pendingKnockTargetIds?.has(exit.targetSceneId) ?? false;

  if (!door) {
    return { showKnock: false, label: "", disabled: false };
  }

  const effectiveState: DoorState = doorState ?? "closed";

  if (effectiveState === "open" || effectiveState === "broken") {
    return {
      showKnock: false,
      label: "",
      disabled: false,
      statusChip: statusLabelForDoor(effectiveState),
    };
  }

  if (pending) {
    return { showKnock: true, label: "Pending", disabled: true };
  }

  if (effectiveState === "closed" || effectiveState === "unlocked") {
    return {
      showKnock: true,
      label: "Knock",
      disabled: false,
      statusChip: effectiveState === "unlocked" ? "Unlocked" : undefined,
    };
  }

  return { showKnock: false, label: "", disabled: false };
}

type RawExitJson = {
  exitId: string;
  label: string;
  targetSceneId: string;
  direction?: string;
  doorState?: string;
  kind?: string;
};

/** Build exit rows from scene JSON, merged with spatial-graph edges. */
export function buildMergedExits(
  exitsJson: string | undefined,
  graph: SpatialGraph | null,
  activeSceneId: string
): ExitRow[] {
  const raw: RawExitJson[] = exitsJson ? JSON.parse(exitsJson) : [];
  return raw.map((ex) => {
    const row: ExitRow = {
      exitId: ex.exitId,
      label: ex.label,
      targetSceneId: ex.targetSceneId,
      direction: ex.direction,
      doorState: ex.doorState,
      kind: ex.kind,
    };
    return mergeExitWithGraphEdge(row, graph?.edges, activeSceneId);
  });
}

type SignalRow = {
  sourceSceneId: string;
  targetSceneId: string;
  kind: string;
  status?: string;
};

/** Target scene IDs with a pending knock from the active scene. */
export function pendingKnockTargets(
  signals: SignalRow[],
  activeSceneId: string
): Set<string> {
  const set = new Set<string>();
  for (const s of signals) {
    if (
      s.sourceSceneId === activeSceneId &&
      s.kind === "knock" &&
      (s.status === "pending" || s.status == null)
    ) {
      set.add(s.targetSceneId);
    }
  }
  return set;
}
