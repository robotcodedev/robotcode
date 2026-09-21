"""Tests for pickling the documentation model.

`KeywordDoc` and `ArgumentInfo` are stored in the library documentation cache.
Entries written before a field existed must load with the default of that
field.
"""

import pickle

from robotcode.robot.diagnostics.library_doc import ArgumentInfo, KeywordArgumentKind, KeywordDoc


def _keyword() -> KeywordDoc:
    return KeywordDoc(
        line_no=1,
        col_offset=-1,
        end_line_no=-1,
        end_col_offset=-1,
        source="Lib.py",
        name="Paint",
        libname="Lib",
        libtype="LIBRARY",
        arguments=[
            ArgumentInfo(
                name="shade",
                str_repr="shade: Shade",
                kind=KeywordArgumentKind.POSITIONAL_OR_NAMED,
                required=True,
                types=["Shade"],
                doc="The shade to use.",
                type_docs={"Color": "Color"},
            )
        ],
        doc="Paints something.",
        return_type="Shade",
        return_doc="The used shade.",
        raises=[("ValueError", "If the shade is unknown.")],
        return_type_docs={"Color": "Color"},
        extra_argument_docs=[("timeout", "Accepted via kwargs.")],
    )


def test_documentation_fields_survive_a_pickle_round_trip() -> None:
    loaded = pickle.loads(pickle.dumps(_keyword()))

    assert loaded.return_doc == "The used shade."
    assert loaded.raises == [("ValueError", "If the shade is unknown.")]
    assert loaded.return_type_docs == {"Color": "Color"}
    assert loaded.extra_argument_docs == [("timeout", "Accepted via kwargs.")]
    assert loaded.arguments[0].doc == "The shade to use."
    assert loaded.arguments[0].type_docs == {"Color": "Color"}
    assert loaded == _keyword()


def test_state_without_the_documentation_fields_yields_the_defaults() -> None:
    keyword = _keyword()
    state = keyword.__getstate__()
    for name in ("return_doc", "raises", "return_type_docs", "extra_argument_docs"):
        del state[name]

    argument = keyword.arguments[0]
    argument_state = {slot: getattr(argument, slot) for slot in argument.__slots__}
    for name in ("doc", "type_docs"):
        del argument_state[name]
    legacy_argument = ArgumentInfo.__new__(ArgumentInfo)
    legacy_argument.__setstate__(argument_state)
    state["arguments"] = [legacy_argument]

    legacy = KeywordDoc.__new__(KeywordDoc)
    legacy.__setstate__(state)

    assert legacy.return_doc == ""
    assert legacy.raises is None
    assert legacy.return_type_docs is None
    assert legacy.extra_argument_docs is None
    assert legacy.arguments[0].doc == ""
    assert legacy.arguments[0].type_docs is None
    assert legacy.arguments[0].name == "shade"
    assert legacy.name == "Paint"
