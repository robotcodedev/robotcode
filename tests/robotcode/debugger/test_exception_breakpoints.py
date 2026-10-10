from robotcode.debugger.dap_types import ExceptionFilterOptions
from robotcode.debugger.debugger import Debugger
from robotcode.debugger.default_capabilities import DFEAULT_CAPABILITIES


def test_every_advertised_exception_filter_is_accepted() -> None:
    """A filter the client can tick has to take effect, not be reported as unverified."""
    filters = [f.filter for f in DFEAULT_CAPABILITIES.exception_breakpoint_filters or []]
    assert "failed_test" in filters

    try:
        result = Debugger.instance.set_exception_breakpoints(
            [], [ExceptionFilterOptions(filter_id=filter_id) for filter_id in filters]
        )
        assert result is not None
        assert [bp.verified for bp in result] == [True] * len(filters)
    finally:
        Debugger.instance.set_exception_breakpoints([])
