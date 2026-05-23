"""Detect whether the current process runs inside an AI agent session.

There is no agreed-upon standard yet — we check a union of variables
known to be set by popular tools (Claude Code, Cursor, Copilot CLI,
OpenCode, Codex, …), plus the proposed generic conventions ``AI_AGENT``
and ``AGENT``. When any of them is set to a truthy value, callers use
the result to flip presentation defaults (colour, pager, REPL plain
backend) so agents get clean stdin/stdout without users having to pass
``--no-color`` / ``--no-pager`` / ``--plain`` on every invocation.

Override hatches:

- ``ROBOTCODE_FORCE_AI_AGENT=1`` — force the detection on (for testing
  and for cases where a marker variable isn't recognised yet).
- ``ROBOTCODE_NO_AI_AGENT=1`` — force the detection off, regardless of
  any other marker.
"""

import os
from typing import Final, Tuple

_AGENT_ENV_VARS: Final[Tuple[str, ...]] = (
    # Generic / proposed standards
    "AI_AGENT",
    "AGENT",
    # Anthropic
    "CLAUDECODE",
    "CLAUDE_CODE",
    # Cursor
    "CURSOR_AGENT",
    "CURSOR_TRACE_ID",
    # OpenAI Codex (set on every subprocess Codex spawns)
    "CODEX_CI",
    "CODEX_THREAD_ID",
    "CODEX_SANDBOX",  # macOS-Seatbelt only; treated as a secondary signal
    # Google
    "GEMINI_CLI",
    "ANTIGRAVITY_AGENT",
    # GitHub Copilot — COPILOT_AGENT is set in terminals launched from
    # VS Code Copilot Chat / agent mode (see microsoft/vscode#311734);
    # COPILOT_AGENT_SESSION_ID is set on every shell command and MCP
    # server the standalone Copilot CLI spawns (>= 0.0.429, April 2026).
    "COPILOT_AGENT",
    "COPILOT_AGENT_SESSION_ID",
    # Microsoft VS Code (1.121+): set when a terminal command is launched
    # by the VS Code agent flow (Copilot Chat) rather than a human.
    "VSCODE_AGENT",
    # opencode (sets both OPENCODE and AGENT)
    "OPENCODE",
    "OPENCODE_CLIENT",  # legacy / Vercel-detection compat
    # Misc agents
    "AUGMENT_AGENT",
    "CLINE_ACTIVE",
)

_FORCE_ON_VAR: Final = "ROBOTCODE_FORCE_AI_AGENT"
_FORCE_OFF_VAR: Final = "ROBOTCODE_NO_AI_AGENT"


def _is_active(var: str) -> bool:
    """A marker var is "active" when it is present in the environment
    with any value other than the empty string or ``"0"``.

    Different agents put very different things in their marker (``1``,
    the agent's name, a session id, …), so anything we'd treat as
    "no, you weren't serious" risks fighting the agent. Only the
    explicit ``=0`` opt-out and absence count as off.
    """
    value = os.environ.get(var)
    if value is None:
        return False
    return value.strip() not in ("", "0")


def is_running_in_ai_agent() -> bool:
    """True when any known agent-marker env var is active.

    `ROBOTCODE_FORCE_AI_AGENT` wins over everything; `ROBOTCODE_NO_AI_AGENT`
    wins over the tool-specific markers but loses to `ROBOTCODE_FORCE_AI_AGENT`.
    """
    if _is_active(_FORCE_ON_VAR):
        return True
    if _is_active(_FORCE_OFF_VAR):
        return False
    return any(_is_active(var) for var in _AGENT_ENV_VARS)


def detected_agent_marker() -> str:
    """Name of the first active env var, or ``""`` when none is set.

    Returns the override-var name when one of them dictated the result;
    otherwise the first tool-specific marker found, in the order listed
    in `_AGENT_ENV_VARS`. For diagnostics / debug logging only.
    """
    if _is_active(_FORCE_ON_VAR):
        return _FORCE_ON_VAR
    if _is_active(_FORCE_OFF_VAR):
        return ""
    for var in _AGENT_ENV_VARS:
        if _is_active(var):
            return var
    return ""
