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
pip install -r requirements.txt
python main.py tests/example-logs.tar.gz
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
