# OpenClaw Agent + Harness

Unified repository for the OpenClaw agent configuration and harness review.

## Structure

```
.
├── agent/              # Agent persona, rules, identity
│   ├── AGENTS.md       # Core instructions, gating, guard rails
│   ├── SOUL.md         # Personality and vibe
│   ├── USER.md         # Human context
│   ├── IDENTITY.md     # Agent identity
│   ├── PHILOSOPHY.md   # Nyanbook philosophy
│   ├── TOOLS.md        # Local setup notes
│   └── HEARTBEAT.md    # Heartbeat checklist
├── harness/            # OpenClaw runtime harness (for bloat audit)
│   ├── docs/           # 45 markdown docs (context injection source)
│   ├── skills/         # 58 skill definitions
│   ├── dist-prompts/   # Runtime prompt construction files
│   └── package.json    # Dependency tree
├── config/             # Credential templates (safe to commit)
│   ├── .env.example    # Env var template
│   ├── openclaw.json.template  # Config template
│   └── secrets.template.json   # Secrets template
├── memory/             # Daily logs (gitignored)
└── .gitignore          # Excludes secrets, memory, .openclaw/
```

## Security

- **No credentials in this repo.** All templates use placeholders.
- Real credentials live in `~/.openclaw/openclaw.json` (outside git).
- See `config/` for the shape of secrets — copy and fill locally.

## Gating Model

| Mode | Purpose | Who | Tools |
|------|---------|-----|-------|
| **describe** | Chat, Q&A | Anyone | Read-only |
| **scribe** | Writing, drafting | Server members | Limited tools |
| **prescribe** | Code, execution | Owner only | Full access |

## Bloat Audit Targets

1. `harness/docs/` — 15M of markdown injected every session
2. `agent/AGENTS.md` — 14KB of instructions
3. Session transcript growth — no auto-compaction
4. Context budget — no hard limit enforcement

See `agent/AGENTS.md` for full guard rails and self-resuscitation protocol.
