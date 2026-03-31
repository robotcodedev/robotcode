from typing import Literal


def test_literal(value: Literal["a", "b", "c"]) -> None:
    print(f"Received value: {value}")
