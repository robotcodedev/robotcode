import threading
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import CamelSnakeMixin, from_dict
from robotcode.core.utils.path import path_is_relative_to


class WorkspaceFolder:
    def __init__(self, name: str, uri: Uri) -> None:
        super().__init__()
        self.name = name
        self.uri = uri


_F = TypeVar("_F", bound=Callable[..., Any])


def config_section(name: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__config_section__", name)
        return func

    return decorator


class ConfigBase(CamelSnakeMixin):
    __config_section__: ClassVar[str]


TConfig = TypeVar("TConfig", bound=ConfigBase)


class Workspace:
    def __init__(
        self,
        root_uri: Optional[Uri],
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
        settings: Dict[str, Any] = {},
    ):
        super().__init__()

        self.root_uri = root_uri
        self._settings = settings

        self._workspace_folders_lock = threading.RLock()
        self._workspace_folders: List[WorkspaceFolder] = workspace_folders if workspace_folders else []

    @property
    def workspace_folders(self) -> List[WorkspaceFolder]:
        with self._workspace_folders_lock:
            return self._workspace_folders

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @settings.setter
    def settings(self, value: Dict[str, Any]) -> None:
        self._settings = value

    def get_configuration(
        self,
        section: Type[TConfig],
        scope_uri: Union[str, Uri, None] = None,
    ) -> TConfig:
        result = self.settings
        for sub_key in str(section).split("."):
            if sub_key in result:
                result = result.get(sub_key, None)
            else:
                result = {}
                break

        return from_dict(result if result else {}, section)

    def get_workspace_folder(self, uri: Union[Uri, str]) -> Optional[WorkspaceFolder]:
        if isinstance(uri, str):
            uri = Uri(uri)

        result = sorted(
            [f for f in self.workspace_folders if path_is_relative_to(uri.to_path(), f.uri.to_path())],
            key=lambda v1: len(v1.uri),
            reverse=True,
        )

        if len(result) > 0:
            return result[0]

        return None
