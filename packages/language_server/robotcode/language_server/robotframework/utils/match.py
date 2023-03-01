from functools import lru_cache


@lru_cache(maxsize=5000)
def normalize(text: str) -> str:
    return text.lower().replace("_", "").replace(" ", "")


def eq(str1: str, str2: str) -> bool:
    str1 = normalize(str1)
    str2 = normalize(str2)
    return str1 == str2
