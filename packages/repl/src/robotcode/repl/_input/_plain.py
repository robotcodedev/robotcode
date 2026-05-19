"""Plain input backend — the historical behaviour, no history / no completion."""


class PlainBackend:
    """Wraps `builtins.input` 1:1.

    Used as the final fallback when no richer backend is available.
    `prefill` is intentionally ignored — there is no editor to seed.
    """

    def read_line(
        self,
        prompt: str,
        *,
        multiline_continuation: bool = False,
        prefill: str = "",
    ) -> str:
        del multiline_continuation, prefill  # plain input has no editor
        return input(prompt)
