from .dap_types import Capabilities, ExceptionBreakpointsFilter

DFEAULT_CAPABILITIES = Capabilities(
    supports_configuration_done_request=True,
    supports_conditional_breakpoints=True,
    supports_hit_conditional_breakpoints=True,
    support_terminate_debuggee=True,
    supports_evaluate_for_hovers=True,
    supports_terminate_request=True,
    supports_log_points=True,
    supports_set_expression=True,
    supports_set_variable=True,
    supports_value_formatting_options=True,
    exception_breakpoint_filters=[
        ExceptionBreakpointsFilter(
            filter="failed_keyword",
            label="Failed Keywords",
            description="Breaks on failed keywords",
            default=False,
            supports_condition=True,
        ),
        ExceptionBreakpointsFilter(
            filter="uncaught_failed_keyword",
            label="Uncaught Failed Keywords",
            description="Breaks on uncaught failed keywords",
            default=True,
            supports_condition=True,
        ),
        ExceptionBreakpointsFilter(
            filter="failed_test",
            label="Failed Test",
            description="Breaks on failed tests",
            default=False,
            supports_condition=True,
        ),
        ExceptionBreakpointsFilter(
            filter="failed_suite",
            label="Failed Suite",
            description="Breaks on failed suite",
            default=False,
            supports_condition=True,
        ),
    ],
    supports_exception_options=True,
    supports_exception_filter_options=True,
    supports_completions_request=True,
    supports_a_n_s_i_styling=True,
)
