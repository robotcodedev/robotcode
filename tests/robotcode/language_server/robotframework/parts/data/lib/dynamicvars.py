from typing import Dict


def get_variables(p: str) -> Dict[str, str]:
    return {
        p + "_A_VAR_FROM_LIB": "1",
    }
