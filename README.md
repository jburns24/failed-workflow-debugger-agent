# Failed Workflow Debugger Agent

This repository packages an **ADK Python agent** that analyzes failed GitHub
Actions workflow runs and posts a Markdown summary of the probable root cause
and suggested fixes.

## Components

| Path | Purpose |
|------|---------|
| `lib/agents/workflow_debugger/agent.py` | ADK agent & helper tool `parse_logs` |
| `main.py` | CLI wrapper (expects `logs.tar.gz`) |
| `Dockerfile` | Container image used by the GitHub Action |
| `action/action.yml` | Re-usable composite action definition |
| `.github/workflows/diagnose.yml` | Example wiring to run after any `CI` workflow failure |

## Quick test locally

```bash
# one-off run
uv pip install .
python main.py /path/to/logs.tar.gz

# or via the helper script (requires gh CLI & .env file):
./scripts/local_diagnose.sh owner/repo 123456789
```

## Publishing / Using the Action

1. Build & push Docker image:

```bash
docker build -t ghcr.io/<org>/failed-workflow-debugger:latest .
docker push ghcr.io/<org>/failed-workflow-debugger:latest
```

2. Tag a release so users can reference `@v1`.

3. In any repo:

```yaml
jobs:
  diagnose:
    if: ${{ failure() }}
    uses: <org>/failed-workflow-debugger-agent@v1
    with:
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Model & API key configuration

This project uses [LiteLLM](https://github.com/BerriAI/litellm) so you can switch between many providers/models without changing code. See the [supported models list](https://docs.litellm.ai/docs/providers) for valid IDs.

| Env var | Purpose | Default |
|---------|---------|---------|
| `OPENAI_API_KEY` (or provider-specific key) | Authenticates the model backend | — (required) |
| `LLM_MODEL` | Model ID, e.g. `openai/gpt-4o`, `anthropic/claude-3-sonnet` | `openai/gpt-4o` |

* **GitHub Action** – accepts an optional `llm_model` input (passed to `LLM_MODEL`) and forwards your secret `OPENAI_API_KEY` into the container.
* **Local script** – place these vars in a `.env` file; `scripts/local_diagnose.sh` loads it automatically.

