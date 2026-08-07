from pathlib import Path
import sys

required = [
    "README.md", "START_HERE.md", "BOOTSTRAP_CONTRACT.md", "MANIFEST.md",
    "AGENTS.md", "CLAUDE.md", "GEMINI.md",
    "docs/INDEX.md", "docs/CURRENT.md", "docs/DECISIONS.md",
    "docs/FOUNDER_AUTOPILOT.md", "docs/FOUNDER_COMMUNICATION.md",
    "docs/CONTEXT_MANAGEMENT.md", "docs/PIPELINE.md", "docs/TOOLING.md",
    "docs/SKILLS.md", "docs/TESTING.md", "docs/RELEASE.md",
    "docs/PIPELINE_UPDATE_RECOMMENDATIONS.md",
    "prompts/start-project-session.md", "prompts/bootstrap-project.md",
    "prompts/investigate-change.md", "prompts/implement-change.md",
    "prompts/verify-change.md", "prompts/test-user-flow.md",
    "prompts/audit-change.md",
    "templates/change/repository-report.md",
    "templates/change/implementation-report.md",
    "templates/change/verification-report.md",
    "templates/change/ux-report.md",
    "templates/change/audit-report.md",
]

forbidden_tokens = (
    "-final", "_final", "-latest", "_latest", "-updated", "_updated",
    "-new", "_new", "-v2", "_v2", "-v3", "_v3",
)

required_skill_sources = (
    "phuryn/pm-skills",
    "mattpocock/skills",
    "coreyhaines31/marketingskills",
)

# Exact private-domain identifiers that must never appear in universal Markdown
# guidance. Kept here, in Python, deliberately — this denylist is not itself
# scanned since the scan below only reads *.md files.
forbidden_domain_phrases = (
    "producer operating kit",
    "ai-assisted music production pipeline",
)

required_phrases = {
    "docs/FOUNDER_AUTOPILOT.md": (
        "The founder is not responsible for",
        "Collaborative strategy and decision rule",
        "The founder and ChatGPT decide the next product move together",
        "When the founder pastes Claude or Codex output",
        "The orchestration hub must automatically",
        "Founder-facing communication",
        "What you should do now",
        "Mandatory manual approval gates",
    ),
    "docs/FOUNDER_COMMUNICATION.md": (
        "Explain-before-routing rule",
        "A recommendation is not approval",
        "What has already happened",
        "What happens next",
        "What the founder needs to decide or do",
        "What you should do now",
        "Do not begin with a status table",
        "Do not attach an unapproved implementation prompt by default",
        "Two-layer output rule",
    ),
    "docs/CONTEXT_MANAGEMENT.md": (
        "The repository stores durable truth",
        "One-ticket execution rule",
        "Fresh-context review",
    ),
    "docs/PIPELINE.md": (
        "Founder Autopilot Mode is the default interface",
        "Founder communication layer",
        "Automatic request routing",
        "Canonical skills-output mapping",
    ),
    "docs/SKILLS.md": (
        "The founder must not be required to",
        "Installation versus activation",
        "Canonical-output rule",
    ),
    "docs/DECISIONS.md": (
        "DEC-014 — Collaborative founder decision rule",
        "the default response is explanation and discussion",
        "DEC-017 — Target-domain / development-governance separation",
    ),
    "AGENTS.md": (
        "Founder Autopilot",
        "Collaborative decision boundary",
        "The founder and ChatGPT brainstorm",
        "Do not automatically generate the next Claude implementation prompt",
        "Founder-friendly communication",
        "The orchestrator selects skills automatically",
        "What you should do now",
        "Never claim success without evidence",
        "Target-domain authority vs development-governance authority",
        "Repository comprehension",
        "No acting agent may silently redesign a target project around Project-Pipeline stages",
    ),
    "CLAUDE.md": (
        "Claude is the default primary production-code implementer",
        "The founder and ChatGPT decide product direction together",
        "Do not assume the next stage has been approved",
    ),
    "START_HERE.md": (
        "Access preflight",
        "Recovery confidence",
        "First response experience",
        "Never require the founder to know or invoke them",
        "What you should do now",
        "Repository identity, at any point in a conversation",
        "It is not scoped only to \"the first meaningful message.\"",
    ),
    "README.md": (
        "Repository identity — read this first",
        "This is a development-governance repository",
        "does not authorize applying the Pipeline",
    ),
    "BOOTSTRAP_CONTRACT.md": (
        "Identify the repository's existing canonical product/domain authorities",
        "Stop and ask the founder when it is unclear whether a requested or discovered change is process-level",
    ),
    "docs/TESTING.md": (
        "Onboarding and repository-identity regression scenarios",
        "Scenario: Project-Pipeline URL pasted mid-conversation",
        "Scenario: README-only agent",
        "Read and understand this repository",
    ),
    "MANIFEST.md": (
        "the project's authority-boundary record",
        "must also record the project's authority-boundary",
    ),
    "prompts/start-project-session.md": (
        "Required founder-facing response",
        "Technical details",
        "What you should do now",
    ),
    "prompts/investigate-change.md": (
        "Founder-facing return",
        "Technical evidence",
        "What you should do now",
    ),
    "prompts/implement-change.md": (
        "Founder-facing return",
        "Technical evidence",
        "What you should do now",
    ),
    "prompts/verify-change.md": (
        "Founder-facing return",
        "Technical evidence",
        "What you should do now",
    ),
    "prompts/test-user-flow.md": (
        "Founder-facing return",
        "Technical evidence",
        "What you should do now",
    ),
    "prompts/audit-change.md": (
        "Founder-facing return",
        "Technical evidence",
        "What you should do now",
    ),
}

template_required_phrases = {
    "templates/change/repository-report.md": ("Founder summary", "Technical evidence"),
    "templates/change/implementation-report.md": ("Founder summary", "Technical evidence"),
    "templates/change/verification-report.md": ("Founder summary", "Technical evidence"),
    "templates/change/ux-report.md": ("Founder summary", "Technical evidence"),
    "templates/change/audit-report.md": ("Founder summary", "Technical evidence"),
}

missing = [path for path in required if not Path(path).is_file()]

bad_names = []
for path in Path(".").rglob("*.md"):
    lowered = path.stem.lower()
    if any(token in lowered for token in forbidden_tokens):
        bad_names.append(str(path))

domain_leaks = []
for path in Path(".").rglob("*.md"):
    if ".git" in path.parts:
        continue
    lowered_text = path.read_text(encoding="utf-8", errors="ignore").lower()
    for phrase in forbidden_domain_phrases:
        if phrase in lowered_text:
            domain_leaks.append(f"{path}: {phrase!r}")

missing_skill_sources = []
skills_doc = Path("docs/SKILLS.md")
if skills_doc.is_file():
    skills_text = skills_doc.read_text(encoding="utf-8")
    missing_skill_sources = [
        source for source in required_skill_sources if source not in skills_text
    ]

missing_phrases = []
for file_path, phrases in required_phrases.items():
    path = Path(file_path)
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in text:
            missing_phrases.append(f"{file_path}: {phrase}")

for file_path, phrases in template_required_phrases.items():
    path = Path(file_path)
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in text:
            missing_phrases.append(f"{file_path}: {phrase}")

if missing:
    print("Missing required pipeline files:")
    for item in missing:
        print(f" - {item}")

if bad_names:
    print("Potential duplicate/versioned document names:")
    for item in bad_names:
        print(f" - {item}")

if missing_skill_sources:
    print("Missing approved skill sources from docs/SKILLS.md:")
    for item in missing_skill_sources:
        print(f" - {item}")

if missing_phrases:
    print("Missing required governance language:")
    for item in missing_phrases:
        print(f" - {item}")

if domain_leaks:
    print("Found real-world domain example in universal guidance:")
    for item in domain_leaks:
        print(f" - {item}")

if missing or bad_names or missing_skill_sources or missing_phrases or domain_leaks:
    sys.exit(1)

print("Universal pipeline checks passed.")