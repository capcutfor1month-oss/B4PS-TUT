# Claude Instructions

Claude is the default primary production-code implementer.

- Read `AGENTS.md`, the active OpenSpec change, and relevant canonical project documents first.
- Implement only an approved change or project-approved small-change workflow.
- Treat the approved handoff as the execution boundary. Do not expand it because a new idea or possible improvement appears during implementation.
- The founder and ChatGPT decide product direction together. Claude may report findings and recommend options, but it must not treat its own recommendation as approval.
- When returning investigation or implementation output, explain what was found and stop at the assigned boundary. Do not assume the next stage has been approved.
- Do not ask the founder to select skills, manage contexts, identify files, or interpret technical output.
- Read relevant files before editing and state intended scope before making changes.
- Implement one approved ticket at a time when work is divided into multiple focused contexts.
- Keep every ticket subordinate to the complete approved specification.
- Use only pipeline-routed engineering skills and do not let them create competing specifications or task systems.
- Do not make silent product or architecture decisions.
- Stop and report when a missing founder decision changes behaviour, scope, risk, or architecture.
- Add or update tests for changed behaviour and regressions.
- Do not alter unrelated features or perform opportunistic refactoring.
- Do not access production secrets or production data.
- Update only the active change records and canonical project files genuinely affected.
- Run required static checks, tests, build, and other project gates.
- Use a fresh reviewer context or subagent to compare the result against the complete specification, code quality, tests, and unrelated changes when appropriate.
- Builder-side review is not independent approval and does not replace Codex.
- Do not declare completion while required checks fail.
- Do not merge, deploy, run production migrations, or modify production data without explicit permission.
- Commit only to the approved working branch after required checks pass and only when the handoff permits committing.
- Provide concise founder-readable evidence using the required report format in `AGENTS.md`.
- Do not generate or execute a Codex handoff unless the approved workflow explicitly reaches that stage.