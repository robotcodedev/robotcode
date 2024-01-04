import os


def show_hidden_arguments() -> bool:
    return os.environ.get("ROBOTCODE_SHOW_HIDDEN_ARGS", "").lower() not in [
        "true",
        "1",
    ]
