"""Plain input backend — the historical behaviour, no history / no completion."""

from typing import List


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

    def get_history(self) -> List[str]:
        return []

    def clear_history(self) -> None:
        pass

    def delete_history_entry(self, idx: int) -> bool:
        del idx
        return False
