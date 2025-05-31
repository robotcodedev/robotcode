import functools

from robotcode.core.utils.version import Version, create_version_from_str


class RoboCopTidyMixin:
    """
    Mixin class for handling Robocop tidy operations.
    """

    @functools.cached_property
    def robotidy_installed(self) -> bool:
        try:
            __import__("robotidy")
        except ImportError:
            return False
        return True

    @functools.cached_property
    def robotidy_version(self) -> Version:
        from robotidy.version import __version__

        return create_version_from_str(__version__)

    @functools.cached_property
    def robotidy_version_str(self) -> str:
        from robotidy.version import __version__

        return str(__version__)

    @functools.cached_property
    def robocop_installed(self) -> bool:
        try:
            __import__("robocop")
        except ImportError:
            return False
        return True

    @functools.cached_property
    def robocop_version(self) -> Version:
        from robocop import __version__

        return create_version_from_str(__version__)

    @functools.cached_property
    def robocop_version_str(self) -> str:
        from robocop import __version__

        return str(__version__)
