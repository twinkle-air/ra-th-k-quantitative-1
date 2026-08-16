# Agent-tool portability

The repository is a standard Agent Skill: `SKILL.md` is the entry point and the application is stored under `assets/app`.

| Tool | User-level location | Project-level location | Typical invocation |
|---|---|---|---|
| Codex | `~/.agents/skills/ra-th-k-quantitative-1` | `.agents/skills/ra-th-k-quantitative-1` | `$ra-th-k-quantitative-1` |
| Claude Code | `~/.claude/skills/ra-th-k-quantitative-1` | `.claude/skills/ra-th-k-quantitative-1` | `/ra-th-k-quantitative-1` |
| WorkBuddy | `~/.workbuddy/skills/ra-th-k-quantitative-1` | `.workbuddy/skills/ra-th-k-quantitative-1` | Ask the agent to use the skill |
| CodeBuddy | `~/.codebuddy/skills/ra-th-k-quantitative-1` | `.codebuddy/skills/ra-th-k-quantitative-1` | Ask the agent to use the skill |

Install for one tool:

```bash
python scripts/install.py --tool codex --scope user
python scripts/install.py --tool claude --scope user
python scripts/install.py --tool workbuddy --scope user
python scripts/install.py --tool codebuddy --scope user
```

Install all supported layouts:

```bash
python scripts/install.py --tool all --scope user
```

For a project-local installation:

```bash
python scripts/install.py --tool all --scope project --project-root /path/to/project
```

The installer copies the complete skill directory and refuses to overwrite an existing installation unless `--force` is supplied. With `--force`, the old installation is moved to a timestamped backup first.

## Runtime

Python 3.10 or newer is recommended. Start the application and create an isolated runtime environment with:

```bash
python scripts/start_app.py --install
```

The first run installs the packages listed in `assets/app/requirements.txt` into `.runtime/venv`. Later runs can omit `--install`.
