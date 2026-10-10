from pathlib import Path

from robotcode.core.lsp.types import (
    ClientCapabilities,
    InitializeParamsClientInfoType,
    TextDocumentSyncOptions,
    WorkspaceFolder,
)
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer


def test_no_requests_that_clients_wait_for_before_changing_or_saving_files(tmp_path: Path) -> None:
    server = RobotLanguageServer()
    protocol = RobotLanguageServerProtocol(server)
    result = protocol._initialize(
        ClientCapabilities(),
        root_path=str(tmp_path),
        root_uri=tmp_path.as_uri(),
        workspace_folders=[WorkspaceFolder(name="test workspace", uri=tmp_path.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
    )
    try:
        workspace = result.capabilities.workspace
        assert workspace is not None
        file_operations = workspace.file_operations
        assert file_operations is not None
        assert file_operations.will_create is None
        assert file_operations.will_rename is None
        assert file_operations.will_delete is None
        assert file_operations.did_create is not None
        assert file_operations.did_rename is not None
        assert file_operations.did_delete is not None

        sync = result.capabilities.text_document_sync
        assert isinstance(sync, TextDocumentSyncOptions)
        assert not sync.will_save_wait_until
    finally:
        protocol._shutdown()
        server.close()
