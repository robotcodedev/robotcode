from functools import lru_cache

_transform_table = str.maketrans("", "", "_ ")

_transform_table_namespace = str.maketrans("", "", " ")


@lru_cache(maxsize=8192)
def normalize(text: str) -> str:
    return text.translate(_transform_table).casefold()


@lru_cache(maxsize=8192)
def normalize_namespace(text: str) -> str:
    return text.translate(_transform_table_namespace).casefold()


def eq(str1: str, str2: str) -> bool:
    str1 = normalize(str1)
    str2 = normalize(str2)
    return str1 == str2


def eq_namespace(str1: str, str2: str) -> bool:
    str1 = normalize_namespace(str1)
    str2 = normalize_namespace(str2)
    return str1 == str2
