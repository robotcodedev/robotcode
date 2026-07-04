from robotcode.analyze.cache.cli import _display_name, _entry_matches


class TestEntryMatches:
    def test_no_patterns_matches_everything(self) -> None:
        assert _entry_matches("/project/suite.robot\nrobot", ()) is True

    def test_plain_entry_matches_by_glob(self) -> None:
        assert _entry_matches("/project/common.resource", ("*.resource",)) is True
        assert _entry_matches("/project/common.resource", ("*.robot",)) is False

    def test_namespace_entry_matches_by_source_glob(self) -> None:
        # namespace entry names carry a "\n<document type>" suffix; a path
        # glob must still match them
        assert _entry_matches("/project/suite.robot\nrobot", ("*/suite.robot",)) is True
        assert _entry_matches("/project/common.resource\nresource", ("*.resource",)) is True

    def test_namespace_entry_matches_by_full_name(self) -> None:
        assert _entry_matches("/project/suite.robot\nrobot", ("*suite.robot*",)) is True

    def test_non_matching_pattern(self) -> None:
        assert _entry_matches("/project/suite.robot\nrobot", ("*/other.robot",)) is False


def test_display_name_keeps_entry_single_line() -> None:
    assert _display_name("/project/suite.robot\nrobot") == "/project/suite.robot · robot"
    assert _display_name("/project/common.resource") == "/project/common.resource"
