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

## Using the Composite GitHub Action

The Action lives at `action/action.yml` and is published via release tags (e.g. `v1.2.0`).

Add it to any repository to annotate failed workflow runs:

```yaml
# .github/workflows/diagnose.yml
name: Diagnose Failures

on:
  workflow_run:
    workflows: ["CI"]     # or whichever workflow(s) you want to watch
    types:
      - completed

jobs:
  diagnose:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - uses: jburns24/failed-workflow-debugger-agent/action@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }} # Required for API calls
          llm_model: "openai/gpt-4o"               # Optional – defaults to same value
          # run_id defaults to the triggering workflow run id
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

The step will:
1. Download the logs for the failed run.
2. Run the agent container to analyse them.
3. Post a rich Markdown report on the PR (or commit).

---

## CI/CD Pipeline (this repo)

The repository ships with an opinionated release flow:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **`ci.yml`** | Every push / PR | Runs intentional-fail tests and executes the debugger Action to dog-food it |
| **`pr-lint.yaml`** | PR events | Enforces Conventional Commit-style PR titles |
| **`semantic-release.yaml`** | Push to `main` | Uses **octo-sts** to acquire a scoped token and creates a new semver tag (`vX.Y.Z`) |
| **`build-push.yaml`** | Push of `v*.*.*` tag | Builds the multi-arch container and pushes `ghcr.io/<owner>/fw-debugger:{sha,latest,version}` |

### Supply-chain verification

* `.github/chainguard/policy.yaml` defines a Chainguard **trust policy** that downstream users can apply to verify provenance.
* `octo-sts` GitHub App must be installed on the repo so `semantic-release.yaml` can request an **OIDC-signed** token to push tags that conform to the policy.

---

## Model & API-key configuration

This project uses [LiteLLM](https://github.com/BerriAI/litellm), so you can point the Action at any supported LLM.

| Env var | Purpose | Default |
|---------|---------|---------|
| `OPENAI_API_KEY` (or provider-specific key) | Authenticates the model backend | — (_required_) |
| `LLM_MODEL` | Model ID, e.g. `openai/gpt-4o`, `anthropic/claude-3-sonnet` | `openai/gpt-4o` |

* **GitHub Action** – accepts an optional `llm_model` input and forwards your secret `OPENAI_API_KEY` into the container.
* **Local script** – place these vars in a `.env` file; `scripts/local_diagnose.sh` loads it automatically.

