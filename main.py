"""CLI entrypoint for the failed-workflow-debugger agent.
Usage: python main.py /path/to/logs.tar.gz
The script extracts raw text from all files inside the tar.gz (GitHub Actions log archive),
feeds it to the ADK agent, and prints the Markdown summary to stdout.
"""
from __future__ import annotations

import sys
import tarfile
from pathlib import Path

from google.adk.runners import Runner

from lib.agents.workflow_debugger.agent import root_agent

MAX_LOG_CHARS = 15000  # avoid blowing the context; tune as needed


def extract_log_text(archive_path: Path) -> str:
    """Extracts and concatenates text files inside a GitHub logs.tar.gz archive."""
    pieces: list[str] = []
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile():
                f = tar.extractfile(member)
                if f:
                    try:
                        txt = f.read().decode("utf-8", errors="ignore")
                        pieces.append(txt)
                    except Exception:
                        continue
    return "\n".join(pieces)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python main.py /path/to/logs.tar.gz", file=sys.stderr)
        sys.exit(1)

    archive_path = Path(sys.argv[1])
    if not archive_path.is_file():
        print(f"Archive {archive_path} not found", file=sys.stderr)
        sys.exit(1)

    logs_text = extract_log_text(archive_path)[:MAX_LOG_CHARS]

    initial_prompt = (
        "Here are the raw logs from the failed workflow run. "
        "Please analyze them and provide a Markdown failure report.\n\n"
        "```text\n" + logs_text + "\n```"
    )

    runner = Runner(agent=root_agent, app_name="failed-workflow-debugger")
    result = runner.run(initial_message=initial_prompt)

    print(result["assistant_response"])


if __name__ == "__main__":
    main()
