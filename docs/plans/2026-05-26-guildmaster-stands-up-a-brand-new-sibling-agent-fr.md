# Build Plan — guildmaster stands up a brand-new sibling agent from one request: a single command creates the public, MIT-licensed, Python repo on GitHub, clones it into the workspace, vendors the full canonical skill kit directly into .claude/skills/, writes a valid CLAUDE.md + culture.yaml identity, and registers it in the ledger — no hand-built scaffold, no issue round-trip

slug: `guildmaster-stands-up-a-brand-new-sibling-agent-fr` · status: `exported` · from frame: `guildmaster-stands-up-a-brand-new-sibling-agent-fr`

> guildmaster stands up a brand-new sibling agent from one request: a single command creates the public, MIT-licensed, Python repo on GitHub, clones it into the workspace, vendors the full canonical skill kit directly into .claude/skills/, writes a valid CLAUDE.md + culture.yaml identity, and registers it in the ledger — no hand-built scaffold, no issue round-trip

## Tasks

### t1 — Scaffold manifest engine: pure afi-cli skeleton file map

- covers: c3, h7
- acceptance:
  - guild/scaffold/manifest.build(agent, desc, backend) returns a relpath->content map containing pyproject.toml, <pkg>/__init__.py, <pkg>/__main__.py, <pkg>/cli/__init__.py, tests/test_cli_chassis.py, .github/workflows/tests.yml, .github/workflows/publish.yml, CHANGELOG.md, README.md, and an MIT LICENSE
  - a test writes the manifest to a tmp dir, runs the generated test, and it passes with zero manual edits (the scaffold builds + self-tests green)

### t2 — Kit-copy planner: content-identical canonical-skill dirs

- covers: c10, h4
- acceptance:
  - guild/scaffold/kit.copy_plan(root) returns a src->dest map covering every canonical skill (iter_skills minus SELF_SKILLS) under .claude/skills/<name>/
  - a test asserts each copied dir is byte-identical to guildmaster's copy (excluding git-ignored skills.local.yaml) and that inbound skills (devague trio) retain their origin attribution

### t3 — Identity generator: CLAUDE.md self-init seed + culture.yaml + skills.local.yaml.example

- covers: c11, c15, h5, h12
- acceptance:
  - guild/scaffold/identity.build(agent, desc, backend) returns CLAUDE.md, culture.yaml, and skills.local.yaml.example contents
  - a test asserts the CLAUDE.md embeds desc, names the agent, and carries an explicit /init-style re-init instruction (h12 a+b); culture.yaml backend matches the prompt file (backend-consistency); no generated file contains an absolute home path

### t4 — Portable workspace-root resolution

- covers: c9, h3
- acceptance:
  - guild/scaffold/workspace.resolve(repo_root, flag, local_cfg) returns --workspace-root if set, else skills.local.yaml's workspace_root key, else repo_root.parent; skills.local.yaml.example documents the workspace_root key
  - a test exercises all three precedence branches and asserts no hardcoded home path is ever returned or embedded

### t5 — Dry-run ProvisionPlan: compose manifest+kit+identity+ledger-diff, zero external

- depends on: t1, t2, t3, t4
- covers: c8, h2
- acceptance:
  - guild/scaffold/plan.build(agent, desc, backend, root, workspace_root) composes manifest+kit+identity+ledger-diff into a ProvisionPlan dataclass and renders it (human + --json)
  - a test asserts building and rendering the dry-run plan performs zero subprocess calls, zero network, and zero file writes outside .devague

### t6 — External-acts executor + boundary guard (the --apply side)

- depends on: t5
- covers: c2, h6, c6, h10
- acceptance:
  - guild/cli/_commands/_provision.apply(plan, runner) runs gh-repo-create(public, MIT, description) -> clone into workspace root -> write manifest -> git add/commit -> git push main, behind an injectable runner
  - it pre-checks the target does not already exist and raises a typed error with no partial scaffold when it does, or when gh auth is missing; only credentials guildmaster already holds are used
  - a test drives a fake runner and asserts the exact command sequence plus the fail-fast-on-existing-target behavior, with no real network

### t7 — guild create command: dry-run default, --apply, ledger registration

- depends on: t5, t6
- covers: c1
- acceptance:
  - guild create --agent X --desc D defaults to dry-run (renders the ProvisionPlan, exit 0, nothing external); --apply runs the executor then registers X in docs/skill-sources.md idempotently; --json emits a structured payload
  - create is registered in the argparse subcommand table; tests cover dry-run-default, --apply happy path (fake runner), and ledger idempotency

### t8 — appsec end-to-end acceptance test (the success signal)

- depends on: t7
- covers: h1, c4, h8, c5, h9, c7, h11
- acceptance:
  - tests/test_create_appsec_acceptance.py runs guild create --agent agentculture/appsec --apply against a sandboxed runner and asserts: repo-create called public+MIT+description, clone present, kit content-identical, identity passes the four steward-doctor invariants (real steward doctor if available, else structural checks), ledger updated
  - a second create for a different agent yields byte-identical kit + identity differing only in agent/desc (reproducibility observable); each assertion is labelled with the target (h1/h4/h5/h8/h9/h11) it validates

### t9 — Docs + guild skill + SELF_SKILLS + version bump

- depends on: t7
- acceptance:
  - guildmaster CLAUDE.md documents guild create under Project shape; the guild skill SKILL.md documents the create surface (single-umbrella-skill convention); create added to SELF_SKILLS
  - version-bump run + CHANGELOG entry added (version-check CI passes); markdownlint-cli2 passes on changed .md files

## Risks

- [unknown_nonblocking] gh repo create --license MIT seeds an initial commit (LICENSE); reconcile with 'push genesis to main' — either create empty + author LICENSE in the manifest, or clone gh's init and commit the scaffold on top (task t6)
- [unknown_nonblocking] apply-path tests must sandbox gh/git (injected runner or a local bare remote) so CI needs no real GitHub credentials (task t6)
- [unknown_nonblocking] steward may not be installed in CI; h1/h5 doctor assertions must run real 'steward doctor' if available, else fall back to structural invariant checks — no hard dependency on a steward checkout (task t8)
