"""Marks that a document gets while the workspace diagnostics loop analyzes it.

The loop notes the marks of a document when it analyzes it, and at the end of
its pass it clears them only when no mark came since. A namespace can become
invalid after the loop analyzed its document with the old namespace; the mark
of that invalidation must keep the document for the next pass.
"""

from pathlib import Path

from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.common.parts.diagnostics import DiagnosticsProtocolPart
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol


def _closed_document(tmp_path: Path) -> TextDocument:
    """A document without a version that the documents manager does not hold, so the loop leaves it alone."""
    return TextDocument(
        document_uri=str(Uri.from_path(tmp_path / "suite.robot")),
        text="*** Test Cases ***\nFirst\n    Log    hello\n",
        language_id="robotframework",
    )


def test_a_mark_after_the_analysis_keeps_the_document_for_the_next_pass(
    protocol: RobotLanguageServerProtocol, tmp_path: Path
) -> None:
    diagnostics = protocol.diagnostics
    document = _closed_document(tmp_path)
    diagnostics.force_refresh_document(document)
    noted = diagnostics._note_marks(document)

    diagnostics.force_refresh_document(document)
    diagnostics.reset_document_diagnostics_data(document, noted)

    assert diagnostics._doc_need_update(document)


def test_without_a_mark_after_the_analysis_the_reset_clears_the_mark(
    protocol: RobotLanguageServerProtocol, tmp_path: Path
) -> None:
    diagnostics = protocol.diagnostics
    document = _closed_document(tmp_path)
    diagnostics.force_refresh_document(document)
    noted = diagnostics._note_marks(document)

    diagnostics.reset_document_diagnostics_data(document, noted)

    assert not diagnostics._doc_need_update(document)


def test_diagnostics_data_replaced_after_the_analysis_keeps_the_document_for_the_next_pass(
    protocol: RobotLanguageServerProtocol, tmp_path: Path
) -> None:
    diagnostics = protocol.diagnostics
    document = _closed_document(tmp_path)
    diagnostics.force_refresh_document(document)
    noted = diagnostics._note_marks(document)

    # the marking of related documents replaces the diagnostics data before it marks the document
    document.set_data(DiagnosticsProtocolPart, None)
    diagnostics.force_refresh_document(document)
    diagnostics.reset_document_diagnostics_data(document, noted)

    assert diagnostics._doc_need_update(document)
