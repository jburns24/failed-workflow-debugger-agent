"""CLI entrypoint for the failed-workflow-debugger agent.
Usage: python main.py /path/to/logs.tar.gz
The script extracts raw text from all files inside the tar.gz (GitHub Actions log archive),
feeds it to the ADK agent, and prints the Markdown summary to stdout.
"""
from __future__ import annotations
import asyncio
import sys
import tarfile
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from lib.agents.workflow_debugger.agent import root_agent

MAX_LOG_CHARS = 20000


import zipfile
import gzip

def extract_log_text(archive_path: Path) -> str:
    """Extract raw text from a GitHub Actions logs archive.

    GitHub's /logs endpoint historically returned a tar.gz archive, but now
    returns a ZIP file. This helper transparently handles both formats by
    attempting tar extraction first and falling back to ZIP if needed.
    """
    pieces: list[str] = []

    # First, try tar.* (tar.gz or uncompressed tar)
    try:
        with tarfile.open(archive_path, "r:*") as tar:
            for member in tar.getmembers():
                if member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        try:
                            txt = f.read().decode("utf-8", errors="ignore")
                            pieces.append(txt)
                        except Exception:
                            continue
            if pieces:
                return "\n".join(pieces)
    except (tarfile.ReadError, gzip.BadGzipFile):
        # Not a tar archive; fall through to try ZIP
        pass

    # Fallback: treat as ZIP
    with zipfile.ZipFile(archive_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            with zf.open(info) as f:
                try:
                    txt = f.read().decode("utf-8", errors="ignore")
                    pieces.append(txt)
                except Exception:
                    continue
    return "\n".join(pieces)


async def main():
    """Entrypoint that runs the debugger agent against a log archive."""
    if len(sys.argv) < 2:
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
        '```text\n' + logs_text + '\n```'
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="failed-workflow-debugger",
        session_service=session_service,
    )

    # Explicit identifiers for the conversational context
    USER_ID = "user_local"
    SESSION_ID = "session_local"

    # Ensure session exists (stateful but in-memory)
    await session_service.create_session(
        app_name=runner.app_name, user_id=USER_ID, session_id=SESSION_ID
    )

    # Prepare the user's message in ADK format
    content = types.Content(role="user", parts=[types.Part(text=initial_prompt)])

    final_response_text = "Agent did not produce a final response."

    # Asynchronously run the agent and capture the final response
    async for event in runner.run_async(
        user_id=USER_ID, session_id=SESSION_ID, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response_text = event.content.parts[0].text
            break

    print(final_response_text)


if __name__ == "__main__":
    asyncio.run(main())
