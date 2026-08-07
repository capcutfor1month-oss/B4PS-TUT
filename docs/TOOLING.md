# Tooling and Skills Registry

| Tool or skill source | Role | Initial status in a new project |
|---|---|---|
| GitHub | Durable source of truth | Active |
| OpenSpec | Change specification and scope | Ready to configure |
| Gemini CLI | Investigation and verification | Ready to configure |
| OpenCode | Low-cost alternate worker | Optional / ready to configure |
| Claude Code | Production implementation | Ready to configure |
| Codex | Independent audit | Ready when a diff exists |
| GitHub Actions | Automated checks | Active for pipeline validation |
| Playwright | Repeatable browser testing | Requires runnable web app |
| Antigravity | Exploratory UX verification | Requires local or preview app |
| `phuryn/pm-skills` | Product discovery, strategy, execution, research, metrics, launch, and AI-shipping frameworks | Approved source; activate by product stage |
| `mattpocock/skills` | Requirement clarification, domain language, TDD, debugging, codebase design, Git guardrails, and handoffs | Approved source; activate by engineering task |
| `coreyhaines31/marketingskills` | Product marketing, research, copy, CRO, SEO, analytics, launch, retention, sales, and growth | Approved source; activate after product context exists |
| Design OS | Complex UX design support | Optional |
| Agent OS | Permanent standards support | Partly represented by agent files |
| Task Master | Large task dependency management | Optional |
| BMAD | Full-team methodology reference | Optional |
| Knowledge Librarian / Project Brain | Optional cross-session project reasoning, decisions, research, history, and continuity | Optional external personal system, not required for pipeline operation — GitHub remains canonical for code, specs, commits, and implementation state; no specific tool (Obsidian, MCP, ChatGPT, Claude, Codex, or another) is assumed available |
| Preview hosting | Safe live testing | Requires approved architecture |
| Production hosting | Public runtime | Requires release candidate |
| Sentry | Technical production monitoring | Requires runtime/framework |
| PostHog | Product behaviour evidence | Requires privacy-safe events |
| GitHub Agentic Workflows | Low-risk repository automation | Add after manual pipeline is stable |

## Skill governance

The canonical external-skill policy lives in `docs/SKILLS.md`.

Approved libraries are capability sources, not mandatory context. Select the smallest relevant skill set for the current stage and task.

### Default stage routing

- Discovery: PM discovery skills plus `grill-with-docs`
- Strategy: PM strategy, value proposition, assumptions, and red-team skills
- Specification: PM PRD, roadmap, user-story, and test-scenario skills plus `to-prd` and `to-issues`
- Implementation: `tdd`, `codebase-design`, and domain modelling when needed
- Debugging: `diagnosing-bugs` plus a regression test
- Launch: product-marketing context, customer research, copywriting, CRO, signup, analytics, and launch skills
- Growth: SEO, experiments, retention, referrals, pricing, email, SMS, social, sales enablement, and revenue operations only when relevant

## Token-efficiency rule

Reserve Claude for implementation. Use scripts, GitHub Actions, Gemini CLI, or OpenCode for exploration, repetitive checks, and log summarization.

Load skills lazily. Do not copy or inject entire upstream libraries into every project or conversation.

## Tool-selection rule

Do not use every tool or skill for every change. Scale the pipeline according to risk, stage, and actual need.
