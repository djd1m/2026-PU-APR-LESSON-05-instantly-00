# Complexity Assessment: Instantly.ai Frontend

## Feature Description
Create a full web frontend for the Instantly.ai cold email outreach platform. React + Vite + Tailwind CSS. Connects to existing FastAPI backend (localhost:8002).

## Dimension Scores

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Files affected | 4 (XL) | 30+ files: React app from scratch — pages, components, hooks, services, router, config |
| Domains touched | 4 (XL) | 6 domains: Auth, Campaigns, Leads, Emails, Analytics, Email Accounts |
| New integrations | 2 (M) | 1: API client to FastAPI backend |
| Breaking changes | 1 (S) | 0 — new frontend, backend untouched |
| New data models | 1 (S) | 0 — frontend consumes existing backend models |
| Cross-cutting concerns | 2 (M) | Auth (JWT), error handling, routing |

**Total Score: 14 → L tier**

## Override Rules
- 2 dimensions at XL (files, domains) → minimum L ✓
- No breaking changes
- New subsystem (entire frontend) → L confirmed

## Classification
- **Tier:** L
- **Active Steps:** 0→1→2→3→3.5→4→5→6→7→8→9
- **Agentic QE Mode:** direct-extended (--full-qe-extended)

## Time Budget
| Phase | Budget |
|-------|--------|
| Requirements | 15 min |
| Planning (ADR+DDD+Arch) | 30 min |
| Implementation | 45 min |
| QE | 30 min |
| **Total** | **2 hours** |

## Active Step Details

| Step | Name | Model | Agentic QE Skill |
|------|------|-------|-----------------|
| 0 | Complexity Router | haiku | — |
| 1 | Requirements | sonnet | — |
| 2 | Research | sonnet | — |
| 3 | ADR + Shift-Left | opus | shift-left-testing |
| 3.5 | QCSD Ideation Swarm | sonnet | qcsd-ideation-swarm |
| 4 | DDD | opus | — |
| 5 | Architecture | opus | — |
| 6 | SPARC-GOAP Plan | sonnet | code-goal-planner |
| 7 | Code | opus | tdd-london-chicago (extended) |
| 8 | QE + Brutal Honesty | sonnet | brutal-honesty-review + mutation-testing + security-testing |
| 9 | Fleet QE | sonnet | 5 core agents + chaos + security + performance |

## Extended Skills Activation Flags
- `HAS_AUTH` = true (JWT authentication) → security-testing activated
- `HAS_EXTERNAL_API` = true (OpenAI integration) → security-testing activated
- `HAS_PERFORMANCE_SLA` = false → performance-testing conditional
- `HAS_INFRASTRUCTURE_CHANGE` = false → chaos-engineering not activated
