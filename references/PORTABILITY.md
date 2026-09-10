# Agent-tool portability

This repository uses the standard Agent Skill bundle layout: a skill directory containing `SKILL.md`, scripts, references, and assets.

| Tool | User-level location | Project-level location | Invocation |
|---|---|---|---|
| Codex | `~/.agents/skills/ra-th-k-quantitative-1` | `.agents/skills/ra-th-k-quantitative-1` | `$ra-th-k-quantitative-1` |
| Claude Code | `~/.claude/skills/ra-th-k-quantitative-1` | `.claude/skills/ra-th-k-quantitative-1` | `/ra-th-k-quantitative-1` |
| WorkBuddy | `~/.workbuddy/skills/ra-th-k-quantitative-1` | `.workbuddy/skills/ra-th-k-quantitative-1` | Ask the agent to use the Skill |
| CodeBuddy | `~/.codebuddy/skills/ra-th-k-quantitative-1` | `.codebuddy/skills/ra-th-k-quantitative-1` | Ask the agent to use the Skill |
| Qoder | `~/.qoder/skills/ra-th-k-quantitative-1` | `.qoder/skills/ra-th-k-quantitative-1` | `/ra-th-k-quantitative-1` or natural language |
| ZCode | `~/.zcode/skills/ra-th-k-quantitative-1` | `.agents/skills/ra-th-k-quantitative-1`, then import to the project | `$ra-th-k-quantitative-1` |
| DeepSeek Harness | `~/.dsh/skills/ra-th-k-quantitative-1` | `.dsh/skills/ra-th-k-quantitative-1` | Ask the harness to use the Skill |

Install one target:

```bash
python scripts/install.py --tool qoder --scope user
python scripts/install.py --tool zcode --scope user
python scripts/install.py --tool deepseek-harness --scope user
```

Install every supported layout:

```bash
python scripts/install.py --tool all --scope user
```

For project-local installation:

```bash
python scripts/install.py --tool all --scope project --project-root /path/to/project
```

The installer copies the complete Skill directory. It refuses to overwrite an existing installation unless `--force` is supplied; forced replacement first creates a timestamped backup. Duplicate destinations used by more than one tool are copied only once.

After installation, Qoder CLI can reload with `/skills reload`. In ZCode, open **Settings -> Skills**, click **Refresh**, and ensure the Skill is enabled. For project scope, use ZCode's Import action to import the entry detected under `.agents/skills`. DeepSeek Harness accepts this repository's direct `<name>/SKILL.md` bundle layout; the deployment's local Skill provider/composition must be enabled.

## Runtime

Python 3.10 or newer is recommended. Start the application and create an isolated runtime environment with:

```bash
python scripts/start_app.py --install
```

The first run installs the packages listed in `assets/app/requirements.txt` into `.runtime/venv`. Later runs can omit `--install`.
