"""Reading the links to the Documentation Viewer in documentation that the language server renders."""

import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

_URI = r"command:robotcode\.showInDocumentationViewer\?[A-Za-z0-9_.~%-]+"
_RE_MARKDOWN_LINK = re.compile(rf"\[((?:[^\[\]\\]|\\.)*)\]\(({_URI}) \"Show in Documentation Viewer\"\)")
_RE_HTML_LINK = re.compile(rf'<a href="({_URI})" title="Show in Documentation Viewer">([^<]*)</a>')
_RE_HEADING_LINK = re.compile(rf"#{{1,6}} \[.*\]\(({_URI}) \"Show in Documentation Viewer\"\)")


def decoded_arguments(uri: str) -> Any:
    """The arguments of a command URI as VS Code reads them: `URI.parse` decodes
    the query, and the command opener decodes it once more before `JSON.parse`."""
    command, _, query = uri.partition("?")
    assert command == "command:robotcode.showInDocumentationViewer"
    return json.loads(urllib.parse.unquote(urllib.parse.unquote(query)))


def viewer_links(markdown: str) -> List[Tuple[str, Dict[str, Any]]]:
    """The text and the target of each link to the Documentation Viewer, in Markdown and in HTML."""
    links = [(text, decoded_arguments(uri)[0]) for text, uri in _RE_MARKDOWN_LINK.findall(markdown)]
    links.extend((text, decoded_arguments(uri)[0]) for uri, text in _RE_HTML_LINK.findall(markdown))
    return links


def viewer_link(markdown: str, text: str) -> Dict[str, Any]:
    """The target of the first link to the Documentation Viewer with the text `text`."""
    target = next((target for link_text, target in viewer_links(markdown) if link_text == text), None)
    assert target is not None, f"no link {text!r} in {markdown!r}"
    return target


def heading_target(markdown: str) -> Optional[Dict[str, Any]]:
    """The target of the link in the first line, `None` if the first line is no heading link."""
    match = _RE_HEADING_LINK.fullmatch(markdown.partition("\n")[0])
    return decoded_arguments(match.group(1))[0] if match else None
