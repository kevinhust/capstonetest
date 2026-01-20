---
description: Implement an approved OpenSpec change and keep tasks in sync.
---
<!-- OPENSPEC:START -->
**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when it is requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `openspec/AGENTS.md` (located inside the `openspec/` directory—run `ls openspec` or `openspec update` if you don't see it) if you need additional OpenSpec conventions or clarifications.

**Steps**
Track these steps as TODOs and complete them one by one.
1. Read `changes/<id>/proposal.md`, `design.md` (if present), and `tasks.md` to confirm scope and acceptance criteria.
2. Work through tasks sequentially, keeping edits minimal and focused on the requested change.
   **Skill Integration (Coding Phase)**:
   - **Frontend/UI**: For any UI components, enforce the 'Frontend Aesthetics Guidelines' (typography, spacing, motion) defined in [frontend-design skill](file:.agent/skills/frontend-design/SKILL.md).
   - **QA**: When writing tests for UI, refer to [webapp-testing skill](file:.agent/skills/webapp-testing/SKILL.md) for Playwright best practices (if applicable).
   **Core Engineering**:
   - **TDD**: Adopt a Test-Driven Development approach. Write the test case in `tests/` *before* implementing the logic in `src/`.
   - **Debugging**: If tests fail, enter 'Debug Mode' (Analysis -> Hypothesis -> Fix -> Verify) before continuing.
3. Confirm completion before updating statuses—make sure every item in `tasks.md` is finished.
4. Update the checklist after all work is done so each task is marked `- [x]` and reflects reality.
5. Reference `openspec list` or `openspec show <item>` when additional context is required.

**Reference**
- Use `openspec show <id> --json --deltas-only` if you need additional context from the proposal while implementing.
<!-- OPENSPEC:END -->
