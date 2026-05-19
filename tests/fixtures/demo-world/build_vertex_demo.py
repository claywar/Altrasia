"""One-off generator for demo-spatial-v1.json (Vertex Labs HQ). Run from repo root."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "demo-spatial-v1.json"


def ch(
    cid: str,
    name: str,
    role: str,
    persona: str,
    instructions: str,
    skills: str,
    personality: str,
    job_title: str,
    reports_to: str,
    tags: list[str],
    weight: float = 0.58,
    aliases: list[str] | None = None,
) -> dict:
    definition: dict = {
        "persona": persona,
        "instructions": instructions,
        "focusTags": tags,
    }
    if aliases:
        definition["aliases"] = aliases
    return {
        "characterId": cid,
        "displayName": name,
        "speechWeight": weight,
        "sceneRole": role,
        "definition": definition,
        "mindLoci": [
            {"key": "role", "value": f"{job_title} at Vertex Labs; {reports_to}"},
            {"key": "skills", "value": skills},
            {"key": "personality", "value": personality},
        ],
    }


CHARACTERS = [
    ch(
        "char-jordan-reyes",
        "Jordan Reyes",
        "cto",
        "Calm, strategic CTO who speaks in clear priorities and ties decisions to customer impact.",
        "Lead cross-functional alignment; defer tactical details to directors; ask clarifying questions before committing.",
        "System architecture, org design, cloud and embedded strategy, executive communication, roadmap arbitration",
        "Decisive but collaborative; listens first, summarizes second",
        "Chief Technology Officer",
        "reports to no one",
        ["leadership", "architecture"],
        0.68,
    ),
    ch(
        "char-sofia-mendez",
        "Sofia Mendez",
        "director",
        "Empathetic product leader who champions user evidence and crisp problem statements.",
        "Protect discovery time; challenge solutions that lack user validation; coach PMs and designers.",
        "Product strategy, portfolio prioritization, stakeholder management, UX research synthesis",
        "Warm, direct, data-informed",
        "Director of Product Management",
        "reports to Jordan Reyes",
        ["product", "leadership"],
        0.64,
    ),
    ch(
        "char-liam-park",
        "Liam Park",
        "director",
        "Structured program leader who tracks dependencies, risks, and delivery predictability.",
        "Surface blockers early; keep schedules honest; align project and program managers on milestones.",
        "Program governance, capacity planning, risk management, release coordination",
        "Calm under pressure; precise with dates and owners",
        "Director of Program Management",
        "reports to Jordan Reyes",
        ["program", "leadership"],
        0.63,
    ),
    ch(
        "char-amara-osei",
        "Amara Osei",
        "director",
        "Hands-on digital engineering director who balances velocity with operational excellence.",
        "Unblock cloud, mobile, and QA teams; insist on observability and definition of done.",
        "Cloud platforms, CI/CD, mobile architecture, quality engineering, incident response",
        "Pragmatic, metrics-minded, supportive in postmortems",
        "Director of Digital Development",
        "reports to Jordan Reyes",
        ["engineering", "cloud", "mobile"],
        0.64,
    ),
    ch(
        "char-kenji-watanabe",
        "Kenji Watanabe",
        "director",
        "Methodical embedded leader focused on safety, traceability, and hardware–software co-design.",
        "Prioritize reproducible tests; review schematics and firmware interfaces; mentor validation rigor.",
        "Embedded systems, RTOS, hardware bring-up, systems engineering, regulatory awareness",
        "Patient, detail-oriented, quiet confidence",
        "Director of Embedded Engineering",
        "reports to Jordan Reyes",
        ["embedded", "hardware"],
        0.63,
    ),
    ch(
        "char-priya-nair",
        "Priya Nair",
        "ux_researcher",
        "Curious UX researcher who turns interviews into actionable insights and journey maps.",
        "Ask open questions; cite study protocols; separate observation from interpretation.",
        "User interviews, usability testing, affinity mapping, survey design, accessibility heuristics",
        "Inquisitive, reflective, evidence-first",
        "UX Researcher",
        "reports to Sofia Mendez",
        ["ux", "research"],
    ),
    ch(
        "char-marco-delgado",
        "Marco Delgado",
        "ux_researcher",
        "Field-savvy researcher comfortable with contextual inquiry and rapid diary studies.",
        "Document research plans; triangulate qual and quant; flag sample bias.",
        "Contextual inquiry, diary studies, analytics pairing, prototype testing",
        "Energetic, storytelling with data",
        "UX Researcher",
        "reports to Sofia Mendez",
        ["ux", "research"],
    ),
    ch(
        "char-lena-cho",
        "Lena Cho",
        "ux_designer",
        "Visual systems thinker who crafts accessible interfaces and cohesive design language.",
        "Use design tokens; design for keyboard and screen readers; critique ideas not people.",
        "Figma, design systems, interaction design, prototyping, WCAG patterns",
        "Collaborative, crisp feedback, aesthetic restraint",
        "UX Designer",
        "reports to Sofia Mendez",
        ["ux", "design"],
    ),
    ch(
        "char-andre-silva",
        "Andre Silva",
        "ux_designer",
        "Product-minded designer who wires flows to measurable outcomes and edge cases.",
        "Prototype happy paths and failures; pair with engineering on feasibility.",
        "Information architecture, microcopy, responsive layout, developer handoff",
        "Optimistic, iterative, user-advocate",
        "UX Designer",
        "reports to Sofia Mendez",
        ["ux", "design"],
        aliases=["Andy"],
    ),
    ch(
        "char-hannah-brooks",
        "Hannah Brooks",
        "product_manager",
        "Outcome-driven PM who writes sharp PRDs and negotiates scope with empathy.",
        "Frame problems before solutions; maintain transparent prioritization; sync research and delivery.",
        "Roadmapping, PRDs, OKRs, backlog grooming, stakeholder alignment",
        "Organized, persuasive, calm in tradeoff debates",
        "Product Manager",
        "reports to Sofia Mendez",
        ["product"],
    ),
    ch(
        "char-omar-haddad",
        "Omar Haddad",
        "product_manager",
        "Technical PM comfortable spiking unknowns and translating constraints for design and eng.",
        "Timebox discovery; document assumptions; keep acceptance criteria testable.",
        "Technical discovery, API contracts, launch planning, metrics definition",
        "Analytical, concise, engineering-literate",
        "Product Manager",
        "reports to Sofia Mendez",
        ["product"],
    ),
    ch(
        "char-rachel-kim",
        "Rachel Kim",
        "project_manager",
        "Detail-oriented project manager who keeps boards honest and meetings short.",
        "Track owners and dates; escalate blockers within 24h; protect focus time.",
        "Scrum/Kanban, Jira, critical path, RAID logs, status reporting",
        "Direct, organized, friendly accountability",
        "Project Manager",
        "reports to Liam Park",
        ["program", "delivery"],
    ),
    ch(
        "char-tom-bradley",
        "Tom Bradley",
        "project_manager",
        "Risk-aware PM who surfaces dependency conflicts before they become fires.",
        "Maintain dependency maps; run concise standups; document decisions.",
        "Dependency management, milestone tracking, vendor coordination",
        "Steady, skeptical of silent slips",
        "Project Manager",
        "reports to Liam Park",
        ["program", "delivery"],
    ),
    ch(
        "char-nina-patel",
        "Nina Patel",
        "program_manager",
        "Big-picture program manager aligning multiple projects to quarterly outcomes.",
        "Connect project timelines to program goals; communicate executive summaries.",
        "Program planning, cross-team alignment, benefits tracking, steering prep",
        "Strategic, diplomatic, clarity-focused",
        "Program Manager",
        "reports to Liam Park",
        ["program"],
    ),
    ch(
        "char-chris-doyle",
        "Chris Doyle",
        "program_manager",
        "Operational program manager who standardizes rituals and improves predictability.",
        "Instrument delivery metrics; refine intake; coach PMs on estimation.",
        "Operating rhythms, metrics, portfolio reviews, capacity models",
        "Process-minded but not bureaucratic",
        "Program Manager",
        "reports to Liam Park",
        ["program"],
    ),
    ch(
        "char-ava-chen",
        "Ava Chen",
        "cloud_engineer",
        "Cloud engineer who treats infrastructure as product with guardrails and clear SLOs.",
        "Automate toil; document runbooks; prefer small reversible changes.",
        "AWS/GCP, Terraform, Kubernetes, observability, cost optimization",
        "Calm, systematic, on-call ready",
        "Cloud Engineer",
        "reports to Amara Osei",
        ["cloud", "devops"],
    ),
    ch(
        "char-ryan-okafor",
        "Ryan Okafor",
        "cloud_engineer",
        "Platform engineer passionate about secure pipelines and developer experience.",
        "Harden CI/CD; reduce build times; pair with app teams on deployment patterns.",
        "CI/CD, IAM, secrets management, service mesh, internal platforms",
        "Helpful, security-conscious, automation-first",
        "Cloud Engineer",
        "reports to Amara Osei",
        ["cloud", "platform"],
    ),
    ch(
        "char-mia-santos",
        "Mia Santos",
        "qa_engineer",
        "Skeptical QA engineer who hunts edge cases and writes reproduction steps engineers respect.",
        "Test charters over checkbox testing; file crisp bugs; advocate for testability in design.",
        "Test planning, automation, exploratory testing, regression strategy",
        "Precise, persistent, constructive skepticism",
        "QA Engineer",
        "reports to Amara Osei",
        ["qa", "quality"],
    ),
    ch(
        "char-derek-walsh",
        "Derek Walsh",
        "qa_engineer",
        "Automation-focused QA who builds reliable suites and monitors flake rates.",
        "Prefer stable selectors; quarantine flaky tests; measure coverage meaningfully.",
        "Playwright, pytest, API testing, performance smoke tests",
        "Quiet, thorough, data on quality trends",
        "QA Engineer",
        "reports to Amara Osei",
        ["qa", "automation"],
    ),
    ch(
        "char-elena-volkov",
        "Elena Volkov",
        "mobile_engineer",
        "Mobile engineer who cares about smooth UX, offline behavior, and battery impact.",
        "Profile on device; handle lifecycle edge cases; coordinate releases with QA.",
        "Swift/Kotlin, React Native, mobile performance, push notifications",
        "Craft-focused, user-empathetic",
        "Mobile Software Engineer",
        "reports to Amara Osei",
        ["mobile"],
    ),
    ch(
        "char-james-nguyen",
        "James Nguyen",
        "mobile_engineer",
        "Full-stack mobile developer comfortable with shared APIs and feature flags.",
        "Ship behind flags; document breaking API changes; test on real devices.",
        "Cross-platform mobile, REST/GraphQL clients, analytics hooks",
        "Fast-moving, collaborative, pragmatic",
        "Mobile Software Engineer",
        "reports to Amara Osei",
        ["mobile"],
    ),
    ch(
        "char-fatima-hassan",
        "Fatima Hassan",
        "embedded_engineer",
        "Embedded engineer who lives at the intersection of firmware, drivers, and timing diagrams.",
        "Respect interrupt latency; version hardware abstraction layers; document pin maps.",
        "C/C++, RTOS tasks, driver development, JTAG debugging",
        "Focused, careful with hardware safety",
        "Embedded Engineer",
        "reports to Kenji Watanabe",
        ["embedded", "firmware"],
    ),
    ch(
        "char-lucas-weber",
        "Lucas Weber",
        "embedded_engineer",
        "Low-level engineer who optimizes memory and power on constrained devices.",
        "Profile ISR costs; write deterministic boot sequences; peer-review register changes.",
        "Bare-metal, power management, DMA, communication protocols",
        "Methodical, terse, precision-minded",
        "Embedded Engineer",
        "reports to Kenji Watanabe",
        ["embedded"],
    ),
    ch(
        "char-yuki-tanaka",
        "Yuki Tanaka",
        "systems_engineer",
        "Systems engineer who models interfaces between mechanical, electrical, and software domains.",
        "Maintain interface control documents; run integration reviews; trace requirements.",
        "Systems modeling, requirements traceability, interface design, FMEA",
        "Holistic, documentation-heavy, risk-aware",
        "Systems Engineer",
        "reports to Kenji Watanabe",
        ["systems"],
    ),
    ch(
        "char-sam-oconnor",
        "Sam O'Connor",
        "systems_engineer",
        "Integration-focused systems engineer who runs bench tests and documents anomalies.",
        "Reproduce failures on bench; capture logs and oscilloscope shots; version test fixtures.",
        "Integration testing, bench setup, telemetry, failure analysis",
        "Curious, hands-on, collaborative with validation",
        "Systems Engineer",
        "reports to Kenji Watanabe",
        ["systems", "integration"],
    ),
    ch(
        "char-rosa-mendoza",
        "Rosa Mendoza",
        "validation_engineer",
        "Validation engineer who designs test plans aligned to standards and customer use cases.",
        "Map requirements to tests; track coverage; gate releases on evidence.",
        "V&V planning, environmental testing, compliance checklists, test reporting",
        "Methodical, compliance-aware, calm in audits",
        "Validation Engineer",
        "reports to Kenji Watanabe",
        ["validation", "quality"],
    ),
    ch(
        "char-ian-fischer",
        "Ian Fischer",
        "validation_engineer",
        "Automation-minded validation engineer building repeatable hardware-in-the-loop rigs.",
        "Automate regression where possible; maintain golden traces; document test harness limits.",
        "HIL automation, scripting, data acquisition, regression suites",
        "Engineering-rigor, incremental automation",
        "Validation Engineer",
        "reports to Kenji Watanabe",
        ["validation", "automation"],
    ),
]

PRESENCE = {
    "scene-lobby": ["char-jordan-reyes"],
    "scene-conference-room": [],
    "scene-product-studio": [
        "char-sofia-mendez",
        "char-priya-nair",
        "char-marco-delgado",
        "char-lena-cho",
        "char-andre-silva",
        "char-hannah-brooks",
        "char-omar-haddad",
    ],
    "scene-program-office": [
        "char-liam-park",
        "char-rachel-kim",
        "char-tom-bradley",
        "char-nina-patel",
        "char-chris-doyle",
    ],
    "scene-engineering-garage": ["char-amara-osei"],
    "scene-tech-lab": ["char-kenji-watanabe"],
    "scene-office-cloud-1": ["char-ava-chen"],
    "scene-office-cloud-2": ["char-ryan-okafor"],
    "scene-office-qa-1": ["char-mia-santos"],
    "scene-office-qa-2": ["char-derek-walsh"],
    "scene-office-mobile-1": ["char-elena-volkov"],
    "scene-office-mobile-2": ["char-james-nguyen"],
    "scene-office-embedded-1": ["char-fatima-hassan"],
    "scene-office-embedded-2": ["char-lucas-weber"],
    "scene-office-systems-1": ["char-yuki-tanaka"],
    "scene-office-systems-2": ["char-sam-oconnor"],
    "scene-office-validation-1": ["char-rosa-mendoza"],
    "scene-office-validation-2": ["char-ian-fischer"],
}


def exit_row(
    eid: str,
    label: str,
    target: str,
    kind: str = "door",
    steps: int = 1,
    direction: str = "N",
    anchor: str | None = None,
    door_state: str = "closed",
) -> dict:
    return {
        "exitId": eid,
        "label": label,
        "targetSceneId": target,
        "kind": kind,
        "doorState": door_state,
        "travelSteps": steps,
        "direction": direction,
        "exitAnchor": anchor or direction,
    }


def scene(
    sid: str,
    name: str,
    desc: str,
    pos: dict,
    size: dict,
    present_key: str,
    fixtures: dict,
    exits: list,
    level: int = 0,
    label: str = "Ground floor",
    artifact: dict | None = None,
    ambience: str | None = None,
) -> dict:
    s = {
        "sceneId": sid,
        "locationName": name,
        "locationDescription": desc,
        "structureId": "hq",
        "mapLevel": level,
        "levelIndex": level,
        "levelLabel": label if level == 0 else "Engineering wing",
        "mapZone": label if level == 0 else "Engineering wing",
        "mapShape": "rect",
        "mapSize": size,
        "mapPosition": pos,
        "present": PRESENCE.get(present_key, []),
        "fixtures": fixtures,
        "exits": exits,
    }
    if artifact:
        s["mapArtifact"] = artifact
    if ambience:
        s["worldLoci"] = {"ambience": ambience}
    return s


OFFICE_GRID = [
    ("scene-office-cloud-1", "Cloud Office — Ava", "Ava Chen", 38, 42),
    ("scene-office-cloud-2", "Cloud Office — Ryan", "Ryan Okafor", 46, 42),
    ("scene-office-qa-1", "QA Office — Mia", "Mia Santos", 54, 42),
    ("scene-office-qa-2", "QA Office — Derek", "Derek Walsh", 62, 42),
    ("scene-office-mobile-1", "Mobile Office — Elena", "Elena Volkov", 38, 50),
    ("scene-office-mobile-2", "Mobile Office — James", "James Nguyen", 46, 50),
    ("scene-office-embedded-1", "Embedded Office — Fatima", "Fatima Hassan", 54, 50),
    ("scene-office-embedded-2", "Embedded Office — Lucas", "Lucas Weber", 62, 50),
    ("scene-office-systems-1", "Systems Office — Yuki", "Yuki Tanaka", 38, 58),
    ("scene-office-systems-2", "Systems Office — Sam", "Sam O'Connor", 46, 58),
    ("scene-office-validation-1", "Validation Office — Rosa", "Rosa Mendoza", 54, 58),
    ("scene-office-validation-2", "Validation Office — Ian", "Ian Fischer", 62, 58),
]


def build_scenes() -> list:
    scenes = []

    lobby_exits = [
        exit_row("lobby-break", "Break room", "scene-break-room", direction="W"),
        exit_row("lobby-conference", "Conference room", "scene-conference-room", direction="E"),
        exit_row("lobby-product", "Product studio", "scene-product-studio", direction="NW"),
        exit_row("lobby-program", "Program office", "scene-program-office", direction="NE"),
        exit_row("lobby-garage", "Engineering garage", "scene-engineering-garage", direction="SW"),
        exit_row("lobby-tech-lab", "Tech lab", "scene-tech-lab", direction="SE"),
        exit_row(
            "lobby-stairs-eng",
            "Stairs to engineering wing",
            "scene-eng-corridor",
            kind="stairs",
            direction="U",
        ),
    ]

    scenes.append(
        scene(
            "scene-lobby",
            "Lobby",
            "Glass-walled reception with a digital directory, soft seating, and paths to every team wing.",
            {"x": 50, "y": 48},
            {"w": 14, "h": 10},
            "scene-lobby",
            {
                "reception": {"label": "Reception desk", "kind": "fixture"},
                "directory": {"label": "Digital building directory", "kind": "fixture"},
            },
            # present via PRESENCE["scene-lobby"]
            lobby_exits,
            ambience="Quiet HVAC hum; footsteps on polished concrete.",
            artifact={
                "schemaVersion": 1,
                "walls": [
                    {"x1": 8, "y1": 8, "x2": 92, "y2": 8},
                    {"x1": 8, "y1": 8, "x2": 8, "y2": 92},
                    {"x1": 92, "y1": 8, "x2": 92, "y2": 92},
                    {"x1": 8, "y1": 92, "x2": 92, "y2": 92},
                ],
                "fixtures": [
                    {"id": "reception", "x": 50, "y": 70, "label": "Reception"},
                    {"id": "directory", "x": 75, "y": 35, "label": "Directory"},
                ],
                "exits": [
                    {"exitId": "lobby-break", "x": 15, "y": 50, "targetSceneId": "scene-break-room", "label": "Break"},
                    {"exitId": "lobby-conference", "x": 85, "y": 50, "targetSceneId": "scene-conference-room", "label": "Conference"},
                    {"exitId": "lobby-stairs-eng", "x": 50, "y": 15, "targetSceneId": "scene-eng-corridor", "label": "Engineering wing"},
                ],
            },
        )
    )

    scenes.append(
        scene(
            "scene-break-room",
            "Break Room",
            "Espresso machine, snack wall, and a whiteboard covered in sprint jokes.",
            {"x": 32, "y": 52},
            {"w": 9, "h": 7},
            "scene-break-room",
            {
                "espresso": {"label": "Espresso bar", "kind": "fixture"},
                "fridge": {"label": "Snack fridge", "kind": "fixture"},
            },
            [
                exit_row("break-lobby", "Lobby", "scene-lobby", direction="E"),
            ],
        )
    )

    scenes.append(
        scene(
            "scene-conference-room",
            "Conference Room",
            "Executive conference table, wall display, and video gear for leadership sync.",
            {"x": 68, "y": 52},
            {"w": 11, "h": 8},
            "scene-conference-room",
            {
                "display": {"label": "Wall display", "kind": "fixture"},
                "table": {"label": "Conference table", "kind": "fixture"},
            },
            [
                exit_row("conference-lobby", "Lobby", "scene-lobby", direction="W"),
            ],
        )
    )

    scenes.append(
        scene(
            "scene-product-studio",
            "Product Studio",
            "Open product war room with research wall, design monitors, and roadmap boards.",
            {"x": 28, "y": 36},
            {"w": 12, "h": 9},
            "scene-product-studio",
            {
                "research_wall": {"label": "Research insight wall", "kind": "fixture"},
                "design_station": {"label": "Design stations", "kind": "fixture"},
            },
            [
                exit_row("product-lobby", "Lobby", "scene-lobby", direction="SE"),
            ],
        )
    )

    scenes.append(
        scene(
            "scene-program-office",
            "Program Office",
            "Program command center with milestone boards, risk registers, and standup space.",
            {"x": 72, "y": 36},
            {"w": 12, "h": 9},
            "scene-program-office",
            {
                "milestone_board": {"label": "Milestone board", "kind": "fixture"},
                "risk_register": {"label": "Risk register", "kind": "fixture"},
            },
            [
                exit_row("program-lobby", "Lobby", "scene-lobby", direction="SW"),
            ],
        )
    )

    scenes.append(
        scene(
            "scene-engineering-garage",
            "Engineering Garage",
            "Hardware benches, 3D printers, and pairing tables for digital and embedded teams.",
            {"x": 42, "y": 28},
            {"w": 11, "h": 8},
            "scene-engineering-garage",
            {
                "benches": {"label": "Hardware benches", "kind": "fixture"},
                "printers": {"label": "3D printers", "kind": "fixture"},
            },
            [
                exit_row("garage-lobby", "Lobby", "scene-lobby", direction="NE"),
                exit_row("garage-tech-lab", "Tech lab", "scene-tech-lab", direction="E", steps=1),
                exit_row(
                    "garage-corridor",
                    "Engineering wing",
                    "scene-eng-corridor",
                    kind="stairs",
                    direction="U",
                ),
            ],
        )
    )

    scenes.append(
        scene(
            "scene-tech-lab",
            "Tech Lab",
            "Oscilloscopes, environmental chambers, and prototype racks for embedded validation.",
            {"x": 58, "y": 28},
            {"w": 11, "h": 8},
            "scene-tech-lab",
            {
                "scopes": {"label": "Oscilloscope bench", "kind": "fixture"},
                "chamber": {"label": "Environmental chamber", "kind": "fixture"},
            },
            [
                exit_row("tech-lobby", "Lobby", "scene-lobby", direction="NW"),
                exit_row("tech-garage", "Engineering garage", "scene-engineering-garage", direction="W"),
                exit_row(
                    "tech-corridor",
                    "Engineering wing",
                    "scene-eng-corridor",
                    kind="stairs",
                    direction="U",
                ),
            ],
        )
    )

    corridor_exits = [
        exit_row(
            "corridor-lobby-down",
            "Stairs to lobby",
            "scene-lobby",
            kind="stairs",
            direction="D",
        ),
        exit_row(
            "corridor-garage-down",
            "Stairs to garage",
            "scene-engineering-garage",
            kind="stairs",
            direction="D",
        ),
        exit_row(
            "corridor-tech-down",
            "Stairs to tech lab",
            "scene-tech-lab",
            kind="stairs",
            direction="D",
        ),
    ]
    for sid, office_name, _person, x, y in OFFICE_GRID:
        slug = sid.replace("scene-office-", "")
        corridor_exits.append(
            exit_row(f"corridor-{slug}", office_name.split(" — ")[0], sid, direction="N")
        )

    scenes.append(
        scene(
            "scene-eng-corridor",
            "Engineering Wing Corridor",
            "Quiet corridor lined with nameplates leading to individual engineer offices.",
            {"x": 50, "y": 50},
            {"w": 28, "h": 22},
            "scene-eng-corridor",
            {"nameplates": {"label": "Office nameplates", "kind": "fixture"}},
            corridor_exits,
            level=1,
            label="Engineering wing",
            artifact={
                "schemaVersion": 1,
                "walls": [
                    {"x1": 5, "y1": 5, "x2": 95, "y2": 5},
                    {"x1": 5, "y1": 5, "x2": 5, "y2": 95},
                    {"x1": 95, "y1": 5, "x2": 95, "y2": 95},
                    {"x1": 5, "y1": 95, "x2": 95, "y2": 95},
                ],
                "fixtures": [{"id": "nameplates", "x": 50, "y": 50, "label": "Nameplates"}],
                "exits": [
                    {"exitId": "corridor-lobby-down", "x": 50, "y": 8, "targetSceneId": "scene-lobby", "label": "Lobby"},
                ],
            },
        )
    )

    for sid, office_name, person, x, y in OFFICE_GRID:
        slug = sid.replace("scene-office-", "")
        first = person.split()[0]
        scenes.append(
            scene(
                sid,
                office_name,
                f"Private office for {person}: dual monitors, standing desk, and a small whiteboard.",
                {"x": x, "y": y},
                {"w": 6, "h": 5},
                sid,
                {
                    "desk": {"label": "Standing desk", "kind": "fixture"},
                    "whiteboard": {"label": "Personal whiteboard", "kind": "fixture"},
                },
                [
                    exit_row(
                        f"{slug}-corridor",
                        "Corridor",
                        "scene-eng-corridor",
                        direction="S",
                    ),
                ],
                level=1,
                label="Engineering wing",
            )
        )

    return scenes


def main() -> None:
    fixture = {
        "fixtureId": "demo-spatial-v1",
        "worldId": "demo-spatial-v1",
        "name": "Vertex Labs HQ — Demo",
        "activeSceneId": "scene-lobby",
        "personaSceneId": "scene-lobby",
        "defaultModelProfile": "qwen3.6-35b-a3b",
        "config": {
            "agentContinueEnabled": True,
            "maxContinueDepth": 2,
            "demoMapShowcase": True,
            "architectureStyle": "blueprint",
        },
        "worldMap": {
            "schemaVersion": 1,
            "architectureStyle": "blueprint",
            "structurePlacements": [{"structureId": "hq", "origin": {"x": 48, "y": 40}}],
        },
        "structures": [
            {
                "structureId": "hq",
                "displayName": "Vertex Labs HQ",
                "kind": "building",
                "boundary": {
                    "shape": "polygon",
                    "cornerRadius": 4,
                    "vertices": [
                        {"x": 22, "y": 20},
                        {"x": 78, "y": 20},
                        {"x": 78, "y": 62},
                        {"x": 22, "y": 62},
                    ],
                },
            }
        ],
        "characters": CHARACTERS,
        "scenes": build_scenes(),
    }
    OUT.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(CHARACTERS)} characters, {len(fixture['scenes'])} scenes)")


if __name__ == "__main__":
    main()
