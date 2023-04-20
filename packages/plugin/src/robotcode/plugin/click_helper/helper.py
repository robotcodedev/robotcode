from enum import Enum
from typing import (
    Any,
    Callable,
    Generic,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import click

T = TypeVar("T", bound=Enum)


class EnumChoice(click.Choice, Generic[T]):
    """A click.Choice that accepts Enum values."""

    def __init__(self, choices: Type[T], case_sensitive: bool = True, excluded: Optional[Set[T]] = None) -> None:
        super().__init__(
            choices if excluded is None else (set(choices).difference(excluded)),  # type: ignore
            case_sensitive,
        )


FC = Union[Callable[..., Any], click.Command]


def add_options(*options: FC) -> FC:
    def _add_options(func: FC) -> FC:
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


class NameParamType(click.types.StringParamType):
    name = "name"

    def __repr__(self) -> str:
        return "NAME"


class AddressParamType(click.types.StringParamType):
    name = "address"

    def __repr__(self) -> str:
        return "ADDRESS"


class PortParamType(click.IntRange):
    name = "port"

    def __init__(self) -> None:
        super().__init__(1, 65535)

    def __repr__(self) -> str:
        return "PORT"


class AddressesPort(NamedTuple):
    addresses: Optional[Sequence[str]] = None
    port: Optional[int] = None


class AddressPortParamType(click.ParamType):
    name = "[<address>:]<port>"

    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> Any:
        splitted = value.split(":")
        if len(splitted) == 1 and splitted[0]:
            try:
                port = PortParamType().convert(splitted[0], param, ctx)
                return AddressesPort(None, port)
            except click.BadParameter:
                if splitted[0].isdigit():
                    raise
                address = AddressParamType().convert(splitted[0], param, ctx)
                return AddressesPort([address], None)

        if len(splitted) == 2:
            address = AddressParamType().convert(splitted[0], param, ctx)
            port = PortParamType().convert(splitted[1], param, ctx)

            return AddressesPort([address], port)

        raise click.BadParameter(f"{value} is not a valid address or port", ctx=ctx, param=param)

    def __repr__(self) -> str:
        return "ADDRESS_PORT"


class MutuallyExclusiveOption(click.Option):
    def __init__(self, *args: Any, mutually_exclusive: Set[str], **kwargs: Any) -> None:
        self.mutually_exclusive = mutually_exclusive
        help = kwargs.get("help", "")
        if self.mutually_exclusive:
            ex_str = ", ".join(self.mutually_exclusive)
            kwargs["help"] = help + ("\n*NOTE:* This option is mutually exclusive with options: " + ex_str + ".")
        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def handle_parse_result(
        self, ctx: click.Context, opts: Mapping[str, Any], args: List[str]
    ) -> Tuple[Any, List[str]]:
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            *first_opts, last_opt = sorted(self.mutually_exclusive)

            raise click.UsageError(
                f"You can't use the --{self.name} option together"
                f" with the --{(', --'.join(first_opts) + ' or the --') if first_opts else ''}{last_opt} option"
            )

        return super(MutuallyExclusiveOption, self).handle_parse_result(ctx, opts, args)
