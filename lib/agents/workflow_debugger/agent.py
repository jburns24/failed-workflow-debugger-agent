"""Workflow Debugger Agent
This ADK agent diagnoses failed GitHub Actions workflow runs. It expects the user (or wrapper script)
to provide the raw logs text as part of the conversation. It extracts error patterns and outputs a
short Markdown summary with probable root causes and suggested fixes.
"""
from __future__ import annotations

import re
from typing import List, Dict

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext

import os

# Model ID can be overridden via env var `LLM_MODEL` (e.g., "anthropic/claude-3-sonnet").
MODEL_ID = os.getenv("LLM_MODEL", "openai/gpt-4o")

COMMON_ERROR_PATTERNS: list[tuple[str, str]] = [
    (r"ModuleNotFoundError: No module named '([^']+)'", "Missing Python dependency: {0}"),
    (r"npm ERR! .* (?:ENOENT|EACCES|npm WARN)|ERR!", "npm/yarn package error"),
    (r"E\s+AssertionError[\s:]+(.+)", "Pytest assertion failed: {0}"),
    (r"Error: Process completed with exit code (\d+)", "Step exited with non-zero code {0}"),
]

def parse_logs(log_lines: List[str], tool_context: ToolContext | None = None) -> Dict[str, object]:
    """Extracts key failure signals from log lines.

    Returns a dict containing a "findings" list with (category, message) tuples.
    """
    findings: list[tuple[str, str]] = []

    joined = "\n".join(log_lines)
    for pattern, template in COMMON_ERROR_PATTERNS:
        for match in re.finditer(pattern, joined):
            msg = template.format(*match.groups())
            findings.append(("error_pattern", msg))

    # Capture first 20 lines around the string "error" as raw context
    context_snips: list[str] = []
    for i, line in enumerate(log_lines):
        if "error" in line.lower():
            snippet = "\n".join(log_lines[max(0, i - 2): i + 3])
            context_snips.append(snippet)
            if len(context_snips) >= 10:
                break

    return {
        "status": "success",
        "findings": findings,
        "snippets": context_snips,
    }


workflow_debugger_agent = Agent(
    name="workflow_debugger",
    model=LiteLlm(model=MODEL_ID),
    instruction=(
        "You diagnose failed GitHub Actions workflow runs. "
        "First, call the tool `parse_logs` to analyse the raw logs passed in the conversation. "
        "Then, combine those findings with any codebase insights you derive. "
        "Output a concise Markdown report containing: \n"
        "1. Probable root cause(s)\n"
        "2. Suggested fix (actionable steps)\n"
        "3. Relevant file names or step links\n"
        "If the failure is ambiguous, say so and propose next investigation steps."
    ),
    description="Analyzes failed GitHub Actions run logs and suggests fixes.",
    tools=[parse_logs],
)

# ADK orchestrators must expose root_agent
root_agent = workflow_debugger_agent
