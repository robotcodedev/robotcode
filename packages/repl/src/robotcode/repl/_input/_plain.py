"""Plain input backend — the historical behaviour, no editor."""


class PlainBackend:
    """Wraps `builtins.input` 1:1.

    The fallback when prompt_toolkit isn't installed (or when the user /
    agent-detection picked plain explicitly). No history, no completion,
    no popup — just stdin/stdout. `prefill` is intentionally ignored;
    there is no editor to seed.
    """

    def read_line(
        self,
        prompt: str,
        *,
        multiline_continuation: bool = False,
        prefill: str = "",
    ) -> str:
        del multiline_continuation, prefill
        return input(prompt)
