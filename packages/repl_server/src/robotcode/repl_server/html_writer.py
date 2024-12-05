from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional, Sequence, TypeVar, Union

from robot.utils.robottime import elapsed_time_to_string

from robotcode.repl.base_interpreter import is_true
from robotcode.robot.utils import get_robot_version


class ElementDataBase:
    def as_str(self, indent: int = 0) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.as_str(0)


_T = TypeVar("_T", bound=ElementDataBase)


class TextElement(ElementDataBase):
    def __init__(self, text: str) -> None:
        self.text = text

    def as_str(self, indent: int = 0) -> str:
        return f"{'  '*indent}{self.text}"


class RawElement(ElementDataBase):
    def __init__(self, text: str) -> None:
        self.text = text

    def as_str(self, indent: int = 0) -> str:
        return f"{'  '*indent}{self.text}"


class Element(ElementDataBase):
    def __init__(
        self,
        tag_name: str,
        text: Optional[str] = None,
        classes: Optional[List[str]] = None,
        styles: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        self.tag_name = tag_name
        self.classes = classes
        self.styles = styles
        if attributes is None:
            attributes = {}
        attributes.update(kwargs)
        self.attributes = attributes
        self.children: List[ElementDataBase] = []

        if text is not None:
            self.add_element(TextElement(text))

    def add_element(self, child: _T) -> _T:
        self.children.append(child)
        return child

    @contextmanager
    def tag(
        self,
        tag_name: str,
        *,
        text: Optional[str] = None,
        classes: Optional[List[str]] = None,
        styles: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Generator["Element", None, None]:
        element = Element(tag_name, text=text, classes=classes, styles=styles, attributes=attributes, **kwargs)

        yield element

        self.add_element(element)

    def add_raw(self, text: Any) -> None:
        self.add_element(RawElement(str(text)))

    def add_text(self, text: Any) -> None:
        self.add_element(TextElement(str(text)))

    def _build_attributes(self) -> str:
        result = []
        if self.classes:
            result.append(f'class="{" ".join(s for s in self.classes if s)}"')
        if self.styles:
            result.append(f'style="{"; ".join(f"{k}: {v}" for k, v in self.styles.items() if v)}"')
        if self.attributes:
            result.extend(f'{k}="{v}"' for k, v in self.attributes.items())

        return " ".join(result)

    NON_BREAKABLE_TAGS = {"span", "a", "b", "i", "u", "strong", "em", "code", "pre", "tt", "samp", "kbd", "var", "td"}

    def as_str(self, indent: int = 0, *, only_children: bool = False) -> str:
        if not only_children:
            attributes = self._build_attributes()

            if attributes:
                start_tag = f"<{self.tag_name} {attributes}>"
            else:
                start_tag = f"<{self.tag_name}>"

            end_tag = f"</{self.tag_name}>"

            result = "  " * indent + start_tag
        else:
            result = ""
            end_tag = None

        if self.children:
            result += "\n" if self.tag_name not in self.NON_BREAKABLE_TAGS else ""
            for child in self.children:
                result += child.as_str((indent + 1) if self.tag_name not in self.NON_BREAKABLE_TAGS else 0) + (
                    "\n" if self.tag_name not in self.NON_BREAKABLE_TAGS else ""
                )
            result += ("  " * indent) if self.tag_name not in self.NON_BREAKABLE_TAGS else ""

        if end_tag:
            result += end_tag

        return result


def create_keyword_html(
    id: Optional[str] = None,
    name: Optional[str] = "",
    owner: Optional[str] = None,
    source_name: Optional[str] = None,
    doc: Optional[str] = "",
    args: Sequence[str] = (),
    assign: Sequence[str] = (),
    tags: Sequence[str] = (),
    timeout: Optional[str] = None,
    type: str = "KEYWORD",
    status: str = "FAIL",
    message: str = "",
    start_time: Union[datetime, str, None] = None,
    end_time: Union[datetime, str, None] = None,
    elapsed_time: Union[timedelta, int, float, None] = None,
    shadow_root_id: Optional[str] = None,
) -> Element:
    result = Element("div", classes=["keyword"], id=id)

    elapsed_time_str = (
        (
            elapsed_time_to_string(elapsed_time)
            if get_robot_version() < (7, 0)
            else elapsed_time_to_string(elapsed_time, seconds=True)
        )
        if elapsed_time is not None
        else ""
    )

    with result.tag(
        "div",
        classes=["element-header", "closed" if status not in ["FAIL"] else ""],
        onclick=f"toggleKeyword('{id}', '{shadow_root_id}')",
    ) as e_element_header:
        with e_element_header.tag(
            "div",
            classes=["element-header-left"],
            title=f"{type.upper()} {owner}.{name} [{status}]",
        ) as e_header_left:
            if elapsed_time is not None:
                with e_header_left.tag("span", classes=["elapsed"]) as e_elapsed:
                    e_elapsed.add_text(elapsed_time_str)
            with e_header_left.tag("span", classes=["label", status.lower()]) as e_label:
                e_label.add_text(str(type).upper())
            with e_header_left.tag("span", classes=["assign"]) as e_assign:
                e_assign.add_text("    ".join(assign))
            with e_header_left.tag("span", classes=["name"]) as e_name:
                with e_name.tag("span", classes=["parent-name"]) as parent_name:
                    parent_name.add_text((owner + " . ") if owner else "")
                e_name.add_text(name)
            e_header_left.add_raw("&nbsp;")
            with e_header_left.tag("span", classes=["arg"]) as args_tag:
                args_tag.add_text("    ".join(args))
        with e_element_header.tag("div", classes=["element-header-right"]) as e_header_right:
            with e_header_right.tag(
                "div",
                classes=["expand"],
                title="Expand all",
                onclick=f"expandAll(event, '{id}', '{shadow_root_id}')",
            ):
                pass
            with e_header_right.tag(
                "div",
                classes=["collapse"],
                title="Collapse all",
                onclick=f"collapseAll(event, '{id}', '{shadow_root_id}')",
            ):
                pass
            with e_header_right.tag(
                "div",
                classes=["link"],
                title="Highlight this item",
                onclick=f"makeElementVisible(event, '{id}', '{shadow_root_id}')",
            ):
                pass
        with e_element_header.tag("div", classes=["element-header-toggle"], title="Toggle visibility"):
            pass

    with result.tag(
        "div", classes=["children", "populated"], styles={"display": "none" if status not in ["FAIL"] else "block"}
    ) as e_children:
        with e_children.tag("table", classes=["metadata", "keyword-metadata"]) as e_body:
            if doc:
                with e_body.tag("tr") as tr:
                    with tr.tag("th", text="Documentation:"):
                        pass
                    with tr.tag("td", classes=["doc"]) as td:
                        td.add_text(doc)
            if tags:
                with e_body.tag("tr") as tr:
                    with tr.tag("th", text="Tags:"):
                        pass
                    with tr.tag("td", classes=["tags"]) as td:
                        td.add_text(", ".join(tags))
            if timeout:
                with e_body.tag("tr") as tr:
                    with tr.tag("th", text="Timeout:"):
                        pass
                    with tr.tag("td", classes=["timeout"]) as td:
                        td.add_text(timeout)
            if source_name:
                with e_body.tag("tr") as tr:
                    with tr.tag("th", text="Source:"):
                        pass
                    with tr.tag("td", classes=["source"]) as td:
                        td.add_text(source_name)
            with e_body.tag("tr") as tr:
                with tr.tag("th", text="Start / End / Elapsed:"):
                    pass
                with tr.tag("td", classes=["message"]) as td:
                    td.add_text(str(start_time) + " / " + str(end_time) + " / " + elapsed_time_str)
            if message:
                with e_body.tag("tr") as tr:
                    with tr.tag("th", text="Message:"):
                        pass
                    with tr.tag("td", classes=["message"]) as td:
                        td.add_text(message)

    return result


def create_message_html(
    id: str,
    message: str,
    level: str,
    html: Union[str, bool] = False,
    timestamp: Union[datetime, str, None] = None,
    shadow_root_id: Optional[str] = None,
) -> Element:
    result = Element("table", classes=["messages", f"{level.lower()}-message"], id=id)

    with result.tag("tr", classes=["message-row"]) as tr:
        with tr.tag("td", classes=["time"]) as td:
            if isinstance(timestamp, datetime):
                td.add_text(timestamp.strftime("%H:%M:%S"))
            else:
                td.add_text(timestamp)
        with tr.tag("td", classes=["level", level.lower()]) as td:
            with td.tag("span", classes=["label", level.lower()]) as sp:
                sp.add_text(level.upper())
        with tr.tag("td", classes=["message"]) as td:
            if is_true(html):
                td.add_raw(message)
            else:
                td.add_text(message)
        with tr.tag(
            "td",
            classes=["select-message"],
            onclick=f"selectMessage('{id}', '{shadow_root_id}')",
            title="Select message text",
        ) as td:
            with td.tag("div"):
                pass

    return result


if __name__ == "__main__":
    # div = Element("div", id="main", classes=["test", "test2"], styles={"color": "red", "font-size": "12px"})
    # p = div.add_element(Element("p", text="Hello, world!"))
    # p.add_element(Element("span", text="This is a test"))
    # print(div)

    # body = Element("body")
    # with body.tag("div", id="main", classes=["test", "test2"], styles={"color": "red"}) as div:
    #     with div.tag("p") as p:
    #         p.add_text("Hello, world!")
    #         with p.tag("span") as span:
    #             span.add_text("This is a test")
    #             with span.tag("br"):
    #                 pass
    #             span.add_text("This is a test")
    #             with span.tag("br", id="test"):
    #                 pass
    # print(body)

    # r = create_keyword_html(
    #     id="ts-1-2-3-4-5-6",
    #     name="Test Keyword",
    #     owner="Test Library",
    #     doc="This is a test keyword",
    #     args=("arg1", "arg2"),
    #     assign=("${var1}", "${var2}"),
    #     tags=("tag1", "tag2"),
    #     timeout="10s",
    #     type="KEYWORD",
    #     status="PASS",
    #     message="This is a test message",
    #     start_time=datetime.now(timezone.utc),
    #     end_time=datetime.now(timezone.utc),
    #     elapsed_time=timedelta(seconds=5),
    # )
    r = create_message_html("ts-1-2-3-4-5-6", "This is a test message", "INFO", timestamp="2021-10-10 12:00:00")
    print(r)
