from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

import pytest
from robotcode.core.dataclasses import as_json, from_json, to_camel_case, to_snake_case
from robotcode.core.lsp.types import (
    CallHierarchyClientCapabilities,
    ClientCapabilities,
    CodeActionClientCapabilities,
    CodeActionClientCapabilitiesCodeActionLiteralSupportType,
    CodeActionClientCapabilitiesCodeActionLiteralSupportTypeCodeActionKindType,
    CodeActionClientCapabilitiesResolveSupportType,
    CodeLensClientCapabilities,
    CodeLensWorkspaceClientCapabilities,
    CompletionClientCapabilities,
    CompletionClientCapabilitiesCompletionItemKindType,
    CompletionClientCapabilitiesCompletionItemType,
    CompletionClientCapabilitiesCompletionItemTypeInsertTextModeSupportType,
    CompletionClientCapabilitiesCompletionItemTypeResolveSupportType,
    CompletionClientCapabilitiesCompletionItemTypeTagSupportType,
    CompletionItemKind,
    CompletionItemTag,
    DeclarationClientCapabilities,
    DefinitionClientCapabilities,
    DiagnosticTag,
    DidChangeConfigurationClientCapabilities,
    DidChangeWatchedFilesClientCapabilities,
    DocumentColorClientCapabilities,
    DocumentFormattingClientCapabilities,
    DocumentHighlightClientCapabilities,
    DocumentLinkClientCapabilities,
    DocumentOnTypeFormattingClientCapabilities,
    DocumentRangeFormattingClientCapabilities,
    DocumentSymbolClientCapabilities,
    DocumentSymbolClientCapabilitiesSymbolKindType,
    DocumentSymbolClientCapabilitiesTagSupportType,
    ExecuteCommandClientCapabilities,
    FailureHandlingKind,
    FileOperationClientCapabilities,
    FoldingRangeClientCapabilities,
    HoverClientCapabilities,
    ImplementationClientCapabilities,
    InitializeParams,
    InitializeParamsClientInfoType,
    InsertTextMode,
    LinkedEditingRangeClientCapabilities,
    MarkupKind,
    PrepareSupportDefaultBehavior,
    PublishDiagnosticsClientCapabilities,
    PublishDiagnosticsClientCapabilitiesTagSupportType,
    ReferenceClientCapabilities,
    RenameClientCapabilities,
    ResourceOperationKind,
    SelectionRangeClientCapabilities,
    SemanticTokensClientCapabilities,
    SemanticTokensClientCapabilitiesRequestsType,
    SemanticTokensClientCapabilitiesRequestsTypeFullType1,
    SemanticTokensWorkspaceClientCapabilities,
    ShowMessageRequestClientCapabilities,
    ShowMessageRequestClientCapabilitiesMessageActionItemType,
    SignatureHelpClientCapabilities,
    SignatureHelpClientCapabilitiesSignatureInformationType,
    SignatureHelpClientCapabilitiesSignatureInformationTypeParameterInformationType,
    SymbolKind,
    SymbolTag,
    TextDocumentClientCapabilities,
    TextDocumentSyncClientCapabilities,
    TokenFormat,
    TraceValues,
    TypeDefinitionClientCapabilities,
    WindowClientCapabilities,
    WorkspaceClientCapabilities,
    WorkspaceEditClientCapabilities,
    WorkspaceEditClientCapabilitiesChangeAnnotationSupportType,
    WorkspaceFolder,
    WorkspaceSymbolClientCapabilities,
    WorkspaceSymbolClientCapabilitiesSymbolKindType,
    WorkspaceSymbolClientCapabilitiesTagSupportType,
)


class EnumData(Enum):
    FIRST = "first"
    SECOND = "second"


@pytest.mark.parametrize(
    ("expr", "expected", "indent", "compact"),
    [
        (1, "1", None, None),
        (True, "true", None, None),
        (False, "false", None, None),
        ("Test", '"Test"', None, None),
        ([], "[]", None, None),
        (["Test"], '["Test"]', None, None),
        (["Test", 1], '["Test", 1]', None, None),
        ({}, "{}", None, None),
        ({"a": 1}, '{"a": 1}', None, None),
        ({"a": 1}, '{\n    "a": 1\n}', True, None),
        ({"a": 1, "b": True}, '{\n    "a": 1,\n    "b": true\n}', True, None),
        ({"a": 1, "b": True}, '{"a":1,"b":true}', None, True),
        ((), "[]", None, None),
        ((1, 2, 3), "[1, 2, 3]", None, None),
        (set(), "[]", None, None),
        ({1, 2}, "[1, 2]", None, None),
        ([EnumData.FIRST, EnumData.SECOND], '["first", "second"]', None, None),
    ],
)
def test_encode_simple(expr: Any, expected: str, indent: Optional[bool], compact: Optional[bool]) -> None:
    assert as_json(expr, indent, compact) == expected


@dataclass
class SimpleItem:
    a: int
    b: int


def test_encode_simple_dataclass() -> None:
    assert as_json(SimpleItem(1, 2)) == '{"a": 1, "b": 2}'


@dataclass
class ComplexItem:
    list_field: List[Any]
    dict_field: Dict[Any, Any]


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        (ComplexItem([], {}), '{"list_field": [], "dict_field": {}}'),
        (
            ComplexItem([1, "2", 3], {"a": "hello", 1: True}),
            '{"list_field": [1, "2", 3], "dict_field": {"a": "hello", "1": true}}',
        ),
    ],
)
def test_encode_complex_dataclass(expr: Any, expected: str) -> None:
    assert as_json(expr) == expected


@dataclass
class ComplexItemWithConfigEncodeCase(ComplexItem):
    @classmethod
    def _encode_case(cls, s: str) -> str:
        return to_camel_case(s)

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return to_snake_case(s)


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        (ComplexItemWithConfigEncodeCase([], {}), '{"listField": [], "dictField": {}}'),
        (
            ComplexItemWithConfigEncodeCase([1, "2", 3], {"a": "hello", 1: True}),
            '{"listField": [1, "2", 3], "dictField": {"a": "hello", "1": true}}',
        ),
    ],
)
def test_encode_complex_dataclass_with_config_encode_case(expr: Any, expected: str) -> None:
    assert as_json(expr) == expected


@dataclass
class SimpleItemWithOptionalField:
    a: Optional[int]


def test_encode_with_optional_field() -> None:
    assert as_json(SimpleItemWithOptionalField(1)) == '{"a": 1}'
    assert as_json(SimpleItemWithOptionalField(None)) == '{"a": null}'


@dataclass
class SimpleItemWithOptionalFieldAndNoneAsDefaultValue:
    a: Optional[int] = None


def test_encode_with_optional_field_and_none_as_default_value() -> None:
    assert as_json(SimpleItemWithOptionalFieldAndNoneAsDefaultValue(1)) == '{"a": 1}'
    assert as_json(SimpleItemWithOptionalFieldAndNoneAsDefaultValue(None)) == "{}"


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ("1", int, 1),
        ('"str"', str, "str"),
        ("1.0", float, 1.0),
        ("true", bool, True),
        ("false", bool, False),
        ('"str"', (str, int), "str"),
        ("1", (int, str), 1),
        ("[]", (int, str, List[int]), []),
        ("[1]", (int, List[int]), [1]),
        ("1", Any, 1),
        ("[]", Union[int, str, List[int]], []),
        ('"first"', EnumData, EnumData.FIRST),
        ('"second"', EnumData, EnumData.SECOND),
        ('["first", "second"]', List[EnumData], [EnumData.FIRST, EnumData.SECOND]),
        ('["first", "second", "ninety"]', List[Union[EnumData, str]], [EnumData.FIRST, EnumData.SECOND, "ninety"]),
    ],
)
def test_decode_simple(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ("{}", dict, {}),
        ('{"a": 1}', dict, {"a": 1}),
        ('{"a": 1}', Dict[str, int], {"a": 1}),
        ('{"a": 1, "b": 2}', Dict[str, int], {"a": 1, "b": 2}),
        ('{"a": 1, "b": null}', Dict[str, Union[int, str, None]], {"a": 1, "b": None}),
        ('{"a": {}, "b": {"a": 2}}', Dict[str, Dict[str, Any]], {"a": {}, "b": {"a": 2}}),
    ],
)
def test_decode_dict(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


# TODO: Tuple is not supported yet
# @pytest.mark.parametrize(
#     ("expr", "type", "expected"),
#     [
#         ("[]", tuple, ()),
#         ("[1]", tuple, (1)),
#         # ('{"a": 1}', Dict[str, int], {"a": 1}),
#         # ('{"a": 1, "b": 2}', Dict[str, int], {"a": 1, "b": 2}),
#         # ('{"a": 1, "b": null}', Dict[str, Union[int, str, None]], {"a": 1, "b": None}),
#         # ('{"a": {}, "b": {"a": 2}}', Dict[str, Dict[str, Any]], {"a": {}, "b": {"a": 2}}),
#     ],
# )
# def test_decode_tuple(expr: Any, type: Any, expected: str) -> None:
#     assert from_json(expr, type) == expected


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"a": 1, "b": 2}', SimpleItem, SimpleItem(1, 2)),
        ('{"b": 2, "a": 1}', SimpleItem, SimpleItem(1, 2)),
        ('{"b": 2, "a": 1}', Optional[SimpleItem], SimpleItem(1, 2)),
    ],
)
def test_decode_simple_class(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


def test_decode_optional_simple_class() -> None:
    assert from_json("null", Optional[SimpleItem]) is None  # type: ignore

    with pytest.raises(TypeError):
        assert from_json("null", SimpleItem) is None


@dataclass
class SimpleItemWithNoFields:
    pass


def test_decode_with_no_fields() -> None:
    assert from_json("{}", SimpleItemWithNoFields) == SimpleItemWithNoFields()


@dataclass
class SimpleItemWithOnlyOptionalFields:
    a: int = 1
    b: int = 2


def test_decode_with_only_optional_fields() -> None:
    assert from_json("{}", SimpleItemWithOnlyOptionalFields) == SimpleItemWithOnlyOptionalFields()


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        (
            '{"listField": [], "dictField": {}}',
            ComplexItemWithConfigEncodeCase,
            ComplexItemWithConfigEncodeCase([], {}),
        ),
        (
            '{"listField": [1,2], "dictField": {"a": 1, "b": "2"}}',
            ComplexItemWithConfigEncodeCase,
            ComplexItemWithConfigEncodeCase([1, 2], {"a": 1, "b": "2"}),
        ),
    ],
)
def test_decode_complex_class_with_encoding(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@dataclass
class SimpleItemWithOptionalFields:
    first: int
    second: bool = True
    third: Optional[str] = None
    forth: Optional[float] = None


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"first": 1}', SimpleItemWithOptionalFields, SimpleItemWithOptionalFields(first=1)),
        (
            '{"first": 1, "third": "Hello"}',
            SimpleItemWithOptionalFields,
            SimpleItemWithOptionalFields(first=1, third="Hello"),
        ),
        ('{"first": 1, "forth": 1.0}', SimpleItemWithOptionalFields, SimpleItemWithOptionalFields(first=1, forth=1.0)),
    ],
)
def test_decode_simple_item_with_optional_field(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@dataclass
class SimpleItem1:
    d: int
    e: int
    f: int = 1


@dataclass
class ComplexItemWithUnionType:
    a_union_field: Union[SimpleItem, SimpleItem1]


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"a_union_field":{"a":1, "b":2}}', ComplexItemWithUnionType, ComplexItemWithUnionType(SimpleItem(1, 2))),
        ('{"a_union_field":{"d":1, "e":2}}', ComplexItemWithUnionType, ComplexItemWithUnionType(SimpleItem1(1, 2))),
        (
            '{"a_union_field":{"d":1, "e":2, "f": 3}}',
            ComplexItemWithUnionType,
            ComplexItemWithUnionType(SimpleItem1(1, 2, 3)),
        ),
    ],
)
def test_decode_with_union_and_different_keys(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@dataclass
class SimpleItem2:
    a: int
    b: int
    c: int = 1


@dataclass
class ComplexItemWithUnionTypeWithSameProperties:
    a_union_field: Union[SimpleItem, SimpleItem2]


def test_decode_with_union_and_some_same_keys() -> None:
    assert from_json(
        '{"a_union_field": {"a": 1, "b":2, "c":3}}', ComplexItemWithUnionTypeWithSameProperties
    ) == ComplexItemWithUnionTypeWithSameProperties(SimpleItem2(1, 2, 3))


def test_decode_with_union_and_same_keys_should_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        from_json('{"a_union_field": {"a": 1, "b":2}}', ComplexItemWithUnionTypeWithSameProperties)


def test_decode_with_union_and_no_keys_should_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        from_json('{"a_union_field": {}}', ComplexItemWithUnionTypeWithSameProperties)


def test_decode_with_union_and_no_match_should_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        from_json('{"a_union_field": {"x": 1, "y":2}}', ComplexItemWithUnionTypeWithSameProperties)


@dataclass
class SimpleItem3:
    a: int
    b: int
    c: int


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"a":1, "b": 2}', (SimpleItem, SimpleItem3), SimpleItem(1, 2)),
        ('{"a":1, "b": 2, "c": 3}', (SimpleItem, SimpleItem3), SimpleItem3(1, 2, 3)),
    ],
)
def test_decode_with_some_same_fields(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


def test_decode_with_some_unambigous_fields_should_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        from_json('{"a":1, "b": 2}', (SimpleItem, SimpleItem2))


@dataclass
class ComplexItemWithUnionTypeWithSimpleAndComplexTypes:
    a_union_field: Union[bool, SimpleItem, SimpleItem1]


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        (
            '{"a_union_field": true}',
            ComplexItemWithUnionTypeWithSimpleAndComplexTypes,
            ComplexItemWithUnionTypeWithSimpleAndComplexTypes(True),
        ),
        (
            '{"a_union_field": {"a":1, "b":2}}',
            ComplexItemWithUnionTypeWithSimpleAndComplexTypes,
            ComplexItemWithUnionTypeWithSimpleAndComplexTypes(SimpleItem(1, 2)),
        ),
    ],
)
def test_decode_union_with_simple_and_complex_types(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


def test_decode_union_with_unknown_keys_should_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        from_json(
            '{"a_union_field": {"d":1, "ef":2}}', ComplexItemWithUnionTypeWithSimpleAndComplexTypes
        ) == ComplexItemWithUnionTypeWithSimpleAndComplexTypes(SimpleItem(1, 2))


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"a":1, "b":2, "c":3}', SimpleItem, SimpleItem(1, 2)),
        ('{"a":1, "b":2, "c":3}', SimpleItemWithOnlyOptionalFields, SimpleItemWithOnlyOptionalFields(1, 2)),
        ('{"a":1}', SimpleItemWithOnlyOptionalFields, SimpleItemWithOnlyOptionalFields(1)),
        ("{}", SimpleItemWithOnlyOptionalFields, SimpleItemWithOnlyOptionalFields()),
        ("{}", SimpleItemWithNoFields, SimpleItemWithNoFields()),
        ('{"a": 1}', SimpleItemWithNoFields, SimpleItemWithNoFields()),
        ('{"a":1, "b":2, "c": 3}', (SimpleItemWithNoFields, SimpleItem), SimpleItem(1, 2)),
    ],
)
def test_decode_non_strict_should_work(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"a":1, "b":2}', SimpleItem, SimpleItem(1, 2)),
        ('{"a":1, "b":2}', SimpleItemWithOnlyOptionalFields, SimpleItemWithOnlyOptionalFields(1, 2)),
        ('{"a":1}', SimpleItemWithOnlyOptionalFields, SimpleItemWithOnlyOptionalFields(1)),
        ("{}", SimpleItemWithOnlyOptionalFields, SimpleItemWithOnlyOptionalFields()),
        ("{}", SimpleItemWithNoFields, SimpleItemWithNoFields()),
        ("{}", (SimpleItemWithNoFields, SimpleItem), SimpleItemWithNoFields()),
        ('{"a":1, "b":2}', (SimpleItemWithNoFields, SimpleItem), SimpleItem(1, 2)),
    ],
)
def test_decode_strict_should_work(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type, strict=True) == expected


@pytest.mark.parametrize(
    ("expr", "type"),
    [
        ('{"a":1, "b": 2, "c": 3}', SimpleItem),
        ('{"a":1, "b": 2, "c": 3}', SimpleItemWithOnlyOptionalFields),
        ('{"a":1, "c": 3}', SimpleItemWithOnlyOptionalFields),
        ('{"c": 3}', SimpleItemWithOnlyOptionalFields),
        ('{"c": 3}', SimpleItemWithNoFields),
    ],
)
def test_decode_strict_with_invalid_data_should_raise_typeerror(expr: Any, type: Any) -> None:
    with pytest.raises(TypeError):
        from_json(expr, type, strict=True)


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('"test"', Literal["test", "blah", "bluff"], "test"),
        ('"bluff"', Literal["test", "blah", "bluff"], "bluff"),
        ('"dada"', (Literal["test", "blah", "bluff"], str), "dada"),
        ("1", (Literal["test", "blah", "bluff"], int), 1),
    ],
)
def test_literal_should_work(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@pytest.mark.parametrize(
    ("expr", "type"),
    [
        ('"dada"', Literal["test", "blah", "bluff"]),
        ('"dada"', (Literal["test", "blah", "bluff"], int)),
    ],
)
def test_literal_with_invalid_args_should_raise_typerror(expr: Any, type: Any) -> None:
    with pytest.raises(TypeError):
        from_json(expr, type)


@dataclass
class SimpleItemWithAlias:
    a: int = field(metadata={"alias": "a_test"})


def test_encode_decode_with_field_alias_should_work() -> None:
    assert from_json('{"a_test": 2}', SimpleItemWithAlias) == SimpleItemWithAlias(2)
    assert as_json(SimpleItemWithAlias(2)) == '{"a_test": 2}'


def test_really_complex_data() -> None:
    data = """\
{
    "processId": 17800,
    "clientInfo": {
        "name": "Visual Studio Code - Insiders",
        "version": "1.62.0-insider"
    },
    "locale": "de",
    "rootPath": "c:\\\\tmp\\\\robottest\\\\dummy\\\\testprj",
    "rootUri": "file:///c%3A/tmp/robottest/dummy/testprj",
    "capabilities": {
        "workspace": {
            "applyEdit": true,
            "workspaceEdit": {
                "documentChanges": true,
                "resourceOperations": [
                    "create",
                    "rename",
                    "delete"
                ],
                "failureHandling": "textOnlyTransactional",
                "normalizesLineEndings": true,
                "changeAnnotationSupport": {
                    "groupsOnLabel": true
                }
            },
            "didChangeConfiguration": {
                "dynamicRegistration": true
            },
            "didChangeWatchedFiles": {
                "dynamicRegistration": true
            },
            "symbol": {
                "dynamicRegistration": true,
                "symbolKind": {
                    "valueSet": [
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26
                    ]
                },
                "tagSupport": {
                    "valueSet": [
                        1
                    ]
                }
            },
            "codeLens": {
                "refreshSupport": true
            },
            "executeCommand": {
                "dynamicRegistration": true
            },
            "configuration": true,
            "workspaceFolders": true,
            "semanticTokens": {
                "refreshSupport": true
            },
            "fileOperations": {
                "dynamicRegistration": true,
                "didCreate": true,
                "didRename": true,
                "didDelete": true,
                "willCreate": true,
                "willRename": true,
                "willDelete": true
            }
        },
        "textDocument": {
            "publishDiagnostics": {
                "relatedInformation": true,
                "versionSupport": false,
                "tagSupport": {
                    "valueSet": [
                        1,
                        2
                    ]
                },
                "codeDescriptionSupport": true,
                "dataSupport": true
            },
            "synchronization": {
                "dynamicRegistration": true,
                "willSave": true,
                "willSaveWaitUntil": true,
                "didSave": true
            },
            "completion": {
                "dynamicRegistration": true,
                "contextSupport": true,
                "completionItem": {
                    "snippetSupport": true,
                    "commitCharactersSupport": true,
                    "documentationFormat": [
                        "markdown",
                        "plaintext"
                    ],
                    "deprecatedSupport": true,
                    "preselectSupport": true,
                    "tagSupport": {
                        "valueSet": [
                            1
                        ]
                    },
                    "insertReplaceSupport": true,
                    "resolveSupport": {
                        "properties": [
                            "documentation",
                            "detail",
                            "additionalTextEdits"
                        ]
                    },
                    "insertTextModeSupport": {
                        "valueSet": [
                            1,
                            2
                        ]
                    }
                },
                "completionItemKind": {
                    "valueSet": [
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25
                    ]
                }
            },
            "hover": {
                "dynamicRegistration": true,
                "contentFormat": [
                    "markdown",
                    "plaintext"
                ]
            },
            "signatureHelp": {
                "dynamicRegistration": true,
                "signatureInformation": {
                    "documentationFormat": [
                        "markdown",
                        "plaintext"
                    ],
                    "parameterInformation": {
                        "labelOffsetSupport": true
                    },
                    "activeParameterSupport": true
                },
                "contextSupport": true
            },
            "definition": {
                "dynamicRegistration": true,
                "linkSupport": true
            },
            "references": {
                "dynamicRegistration": true
            },
            "documentHighlight": {
                "dynamicRegistration": true
            },
            "documentSymbol": {
                "dynamicRegistration": true,
                "symbolKind": {
                    "valueSet": [
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26
                    ]
                },
                "hierarchicalDocumentSymbolSupport": true,
                "tagSupport": {
                    "valueSet": [
                        1
                    ]
                },
                "labelSupport": true
            },
            "codeAction": {
                "dynamicRegistration": true,
                "isPreferredSupport": true,
                "disabledSupport": true,
                "dataSupport": true,
                "resolveSupport": {
                    "properties": [
                        "edit"
                    ]
                },
                "codeActionLiteralSupport": {
                    "codeActionKind": {
                        "valueSet": [
                            "",
                            "quickfix",
                            "refactor",
                            "refactor.extract",
                            "refactor.inline",
                            "refactor.rewrite",
                            "source",
                            "source.organizeImports"
                        ]
                    }
                },
                "honorsChangeAnnotations": false
            },
            "codeLens": {
                "dynamicRegistration": true
            },
            "formatting": {
                "dynamicRegistration": true
            },
            "rangeFormatting": {
                "dynamicRegistration": true
            },
            "onTypeFormatting": {
                "dynamicRegistration": true
            },
            "rename": {
                "dynamicRegistration": true,
                "prepareSupport": true,
                "prepareSupportDefaultBehavior": 1,
                "honorsChangeAnnotations": true
            },
            "documentLink": {
                "dynamicRegistration": true,
                "tooltipSupport": true
            },
            "typeDefinition": {
                "dynamicRegistration": true,
                "linkSupport": true
            },
            "implementation": {
                "dynamicRegistration": true,
                "linkSupport": true
            },
            "colorProvider": {
                "dynamicRegistration": true
            },
            "foldingRange": {
                "dynamicRegistration": true,
                "rangeLimit": 5000,
                "lineFoldingOnly": true
            },
            "declaration": {
                "dynamicRegistration": true,
                "linkSupport": true
            },
            "selectionRange": {
                "dynamicRegistration": true
            },
            "callHierarchy": {
                "dynamicRegistration": true
            },
            "semanticTokens": {
                "dynamicRegistration": true,
                "tokenTypes": [
                    "namespace",
                    "type",
                    "class",
                    "enum",
                    "interface",
                    "struct",
                    "typeParameter",
                    "parameter",
                    "variable",
                    "property",
                    "enumMember",
                    "event",
                    "function",
                    "method",
                    "macro",
                    "keyword",
                    "modifier",
                    "comment",
                    "string",
                    "number",
                    "regexp",
                    "operator"
                ],
                "tokenModifiers": [
                    "declaration",
                    "definition",
                    "readonly",
                    "static",
                    "deprecated",
                    "abstract",
                    "async",
                    "modification",
                    "documentation",
                    "defaultLibrary"
                ],
                "formats": [
                    "relative"
                ],
                "requests": {
                    "range": true,
                    "full": {
                        "delta": true
                    }
                },
                "multilineTokenSupport": false,
                "overlappingTokenSupport": false
            },
            "linkedEditingRange": {
                "dynamicRegistration": true
            }
        },
        "window": {
            "showMessage": {
                "messageActionItem": {
                    "additionalPropertiesSupport": true
                }
            }
        }
    },
    "initializationOptions": {
        "storageUri": "file:///c%3A/Users/daniel/AppData/Roaming/Code%20-%20Insiders/User/workspaceStorage/1ab0e3033b053a024fb7cbf9068380d1/d-biehl.robotcode",
        "globalStorageUri": "file:///c%3A/Users/daniel/AppData/Roaming/Code%20-%20Insiders/User/globalStorage/d-biehl.robotcode"
    },
    "trace": "off",
    "workspaceFolders": [
        {
            "uri": "file:///c%3A/tmp/robottest/dummy/testprj",
            "name": "testprj"
        }
    ],
    "workDoneToken": "76db5c8a-d083-44d0-bfa8-9e004eb69a1d"
}
"""

    assert from_json(data, InitializeParams) == InitializeParams(
        capabilities=ClientCapabilities(
            workspace=WorkspaceClientCapabilities(
                apply_edit=True,
                workspace_edit=WorkspaceEditClientCapabilities(
                    document_changes=True,
                    resource_operations=[
                        ResourceOperationKind.CREATE,
                        ResourceOperationKind.RENAME,
                        ResourceOperationKind.DELETE,
                    ],
                    failure_handling=FailureHandlingKind.TEXT_ONLY_TRANSACTIONAL,
                    normalizes_line_endings=True,
                    change_annotation_support=WorkspaceEditClientCapabilitiesChangeAnnotationSupportType(
                        groups_on_label=True
                    ),
                ),
                did_change_configuration=DidChangeConfigurationClientCapabilities(dynamic_registration=True),
                did_change_watched_files=DidChangeWatchedFilesClientCapabilities(dynamic_registration=True),
                symbol=WorkspaceSymbolClientCapabilities(
                    dynamic_registration=True,
                    symbol_kind=WorkspaceSymbolClientCapabilitiesSymbolKindType(
                        value_set=[
                            SymbolKind.FILE,
                            SymbolKind.MODULE,
                            SymbolKind.NAMESPACE,
                            SymbolKind.PACKAGE,
                            SymbolKind.CLASS,
                            SymbolKind.METHOD,
                            SymbolKind.PROPERTY,
                            SymbolKind.FIELD,
                            SymbolKind.CONSTRUCTOR,
                            SymbolKind.ENUM,
                            SymbolKind.INTERFACE,
                            SymbolKind.FUNCTION,
                            SymbolKind.VARIABLE,
                            SymbolKind.CONSTANT,
                            SymbolKind.STRING,
                            SymbolKind.NUMBER,
                            SymbolKind.BOOLEAN,
                            SymbolKind.ARRAY,
                            SymbolKind.OBJECT,
                            SymbolKind.KEY,
                            SymbolKind.NULL,
                            SymbolKind.ENUM_MEMBER,
                            SymbolKind.STRUCT,
                            SymbolKind.EVENT,
                            SymbolKind.OPERATOR,
                            SymbolKind.TYPE_PARAMETER,
                        ]
                    ),
                    tag_support=WorkspaceSymbolClientCapabilitiesTagSupportType(value_set=[SymbolTag.DEPRECATED]),
                ),
                execute_command=ExecuteCommandClientCapabilities(dynamic_registration=True),
                workspace_folders=True,
                configuration=True,
                semantic_tokens=SemanticTokensWorkspaceClientCapabilities(refresh_support=True),
                code_lens=CodeLensWorkspaceClientCapabilities(refresh_support=True),
                file_operations=FileOperationClientCapabilities(
                    dynamic_registration=True,
                    did_create=True,
                    will_create=True,
                    did_rename=True,
                    will_rename=True,
                    did_delete=True,
                    will_delete=True,
                ),
            ),
            text_document=TextDocumentClientCapabilities(
                synchronization=TextDocumentSyncClientCapabilities(
                    dynamic_registration=True, will_save=True, will_save_wait_until=True, did_save=True
                ),
                completion=CompletionClientCapabilities(
                    dynamic_registration=True,
                    completion_item=CompletionClientCapabilitiesCompletionItemType(
                        snippet_support=True,
                        commit_characters_support=True,
                        documentation_format=[MarkupKind.MARKDOWN, MarkupKind.PLAIN_TEXT],
                        deprecated_support=True,
                        preselect_support=True,
                        tag_support=CompletionClientCapabilitiesCompletionItemTypeTagSupportType(
                            value_set=[CompletionItemTag.DEPRECATED]
                        ),
                        insert_replace_support=True,
                        resolve_support=CompletionClientCapabilitiesCompletionItemTypeResolveSupportType(
                            properties=["documentation", "detail", "additionalTextEdits"]
                        ),
                        insert_text_mode_support=CompletionClientCapabilitiesCompletionItemTypeInsertTextModeSupportType(
                            value_set=[InsertTextMode.AS_IS, InsertTextMode.ADJUST_INDENTATION]
                        ),
                    ),
                    completion_item_kind=CompletionClientCapabilitiesCompletionItemKindType(
                        value_set=[
                            CompletionItemKind.TEXT,
                            CompletionItemKind.METHOD,
                            CompletionItemKind.FUNCTION,
                            CompletionItemKind.CONSTRUCTOR,
                            CompletionItemKind.FIELD,
                            CompletionItemKind.VARIABLE,
                            CompletionItemKind.CLASS,
                            CompletionItemKind.INTERFACE,
                            CompletionItemKind.MODULE,
                            CompletionItemKind.PROPERTY,
                            CompletionItemKind.UNIT,
                            CompletionItemKind.VALUE,
                            CompletionItemKind.ENUM,
                            CompletionItemKind.KEYWORD,
                            CompletionItemKind.SNIPPET,
                            CompletionItemKind.COLOR,
                            CompletionItemKind.FILE,
                            CompletionItemKind.REFERENCE,
                            CompletionItemKind.FOLDER,
                            CompletionItemKind.ENUM_MEMBER,
                            CompletionItemKind.CONSTANT,
                            CompletionItemKind.STRUCT,
                            CompletionItemKind.EVENT,
                            CompletionItemKind.OPERATOR,
                            CompletionItemKind.TYPE_PARAMETER,
                        ]
                    ),
                    context_support=True,
                ),
                hover=HoverClientCapabilities(
                    dynamic_registration=True, content_format=[MarkupKind.MARKDOWN, MarkupKind.PLAIN_TEXT]
                ),
                signature_help=SignatureHelpClientCapabilities(
                    dynamic_registration=True,
                    signature_information=SignatureHelpClientCapabilitiesSignatureInformationType(
                        documentation_format=[MarkupKind.MARKDOWN, MarkupKind.PLAIN_TEXT],
                        parameter_information=SignatureHelpClientCapabilitiesSignatureInformationTypeParameterInformationType(
                            label_offset_support=True
                        ),
                        active_parameter_support=True,
                    ),
                    context_support=True,
                ),
                declaration=DeclarationClientCapabilities(dynamic_registration=True, link_support=True),
                definition=DefinitionClientCapabilities(dynamic_registration=True, link_support=True),
                type_definition=TypeDefinitionClientCapabilities(dynamic_registration=True, link_support=True),
                implementation=ImplementationClientCapabilities(dynamic_registration=True, link_support=True),
                references=ReferenceClientCapabilities(dynamic_registration=True),
                document_highlight=DocumentHighlightClientCapabilities(dynamic_registration=True),
                document_symbol=DocumentSymbolClientCapabilities(
                    dynamic_registration=True,
                    symbol_kind=DocumentSymbolClientCapabilitiesSymbolKindType(
                        value_set=[
                            SymbolKind.FILE,
                            SymbolKind.MODULE,
                            SymbolKind.NAMESPACE,
                            SymbolKind.PACKAGE,
                            SymbolKind.CLASS,
                            SymbolKind.METHOD,
                            SymbolKind.PROPERTY,
                            SymbolKind.FIELD,
                            SymbolKind.CONSTRUCTOR,
                            SymbolKind.ENUM,
                            SymbolKind.INTERFACE,
                            SymbolKind.FUNCTION,
                            SymbolKind.VARIABLE,
                            SymbolKind.CONSTANT,
                            SymbolKind.STRING,
                            SymbolKind.NUMBER,
                            SymbolKind.BOOLEAN,
                            SymbolKind.ARRAY,
                            SymbolKind.OBJECT,
                            SymbolKind.KEY,
                            SymbolKind.NULL,
                            SymbolKind.ENUM_MEMBER,
                            SymbolKind.STRUCT,
                            SymbolKind.EVENT,
                            SymbolKind.OPERATOR,
                            SymbolKind.TYPE_PARAMETER,
                        ]
                    ),
                    hierarchical_document_symbol_support=True,
                    tag_support=DocumentSymbolClientCapabilitiesTagSupportType(value_set=[SymbolTag.DEPRECATED]),
                    label_support=True,
                ),
                code_action=CodeActionClientCapabilities(
                    dynamic_registration=True,
                    code_action_literal_support=CodeActionClientCapabilitiesCodeActionLiteralSupportType(
                        code_action_kind=CodeActionClientCapabilitiesCodeActionLiteralSupportTypeCodeActionKindType(
                            value_set=[
                                "",
                                "quickfix",
                                "refactor",
                                "refactor.extract",
                                "refactor.inline",
                                "refactor.rewrite",
                                "source",
                                "source.organizeImports",
                            ]
                        )
                    ),
                    is_preferred_support=True,
                    disabled_support=True,
                    data_support=True,
                    resolve_support=CodeActionClientCapabilitiesResolveSupportType(properties=["edit"]),
                    honors_change_annotations=False,
                ),
                code_lens=CodeLensClientCapabilities(dynamic_registration=True),
                document_link=DocumentLinkClientCapabilities(dynamic_registration=True, tooltip_support=True),
                color_provider=DocumentColorClientCapabilities(dynamic_registration=True),
                formatting=DocumentFormattingClientCapabilities(dynamic_registration=True),
                range_formatting=DocumentRangeFormattingClientCapabilities(dynamic_registration=True),
                on_type_formatting=DocumentOnTypeFormattingClientCapabilities(dynamic_registration=True),
                rename=RenameClientCapabilities(
                    dynamic_registration=True,
                    prepare_support=True,
                    prepare_support_default_behavior=PrepareSupportDefaultBehavior.IDENTIFIER,
                    honors_change_annotations=True,
                ),
                publish_diagnostics=PublishDiagnosticsClientCapabilities(
                    related_information=True,
                    tag_support=PublishDiagnosticsClientCapabilitiesTagSupportType(
                        value_set=[DiagnosticTag.UNNECESSARY, DiagnosticTag.DEPRECATED]
                    ),
                    version_support=False,
                    code_description_support=True,
                    data_support=True,
                ),
                folding_range=FoldingRangeClientCapabilities(
                    dynamic_registration=True, range_limit=5000, line_folding_only=True
                ),
                selection_range=SelectionRangeClientCapabilities(dynamic_registration=True),
                linked_editing_range=LinkedEditingRangeClientCapabilities(dynamic_registration=True),
                call_hierarchy=CallHierarchyClientCapabilities(dynamic_registration=True),
                semantic_tokens=SemanticTokensClientCapabilities(
                    requests=SemanticTokensClientCapabilitiesRequestsType(
                        range=True, full=SemanticTokensClientCapabilitiesRequestsTypeFullType1(delta=True)
                    ),
                    token_types=[
                        "namespace",
                        "type",
                        "class",
                        "enum",
                        "interface",
                        "struct",
                        "typeParameter",
                        "parameter",
                        "variable",
                        "property",
                        "enumMember",
                        "event",
                        "function",
                        "method",
                        "macro",
                        "keyword",
                        "modifier",
                        "comment",
                        "string",
                        "number",
                        "regexp",
                        "operator",
                    ],
                    token_modifiers=[
                        "declaration",
                        "definition",
                        "readonly",
                        "static",
                        "deprecated",
                        "abstract",
                        "async",
                        "modification",
                        "documentation",
                        "defaultLibrary",
                    ],
                    formats=[TokenFormat.RELATIVE],
                    overlapping_token_support=False,
                    multiline_token_support=False,
                    dynamic_registration=True,
                ),
                moniker=None,
            ),
            window=WindowClientCapabilities(
                work_done_progress=None,
                show_message=ShowMessageRequestClientCapabilities(
                    message_action_item=ShowMessageRequestClientCapabilitiesMessageActionItemType(
                        additional_properties_support=True
                    )
                ),
                show_document=None,
            ),
            general=None,
            experimental=None,
        ),
        process_id=17800,
        client_info=InitializeParamsClientInfoType(name="Visual Studio Code - Insiders", version="1.62.0-insider"),
        locale="de",
        root_path="c:\\tmp\\robottest\\dummy\\testprj",
        root_uri="file:///c%3A/tmp/robottest/dummy/testprj",
        initialization_options={
            "storageUri": "file:///c%3A/Users/daniel/AppData/Roaming/Code%20-%20Insiders/User/workspaceStorage/1ab0e3033b053a024fb7cbf9068380d1/d-biehl.robotcode",
            "globalStorageUri": "file:///c%3A/Users/daniel/AppData/Roaming/Code%20-%20Insiders/User/globalStorage/d-biehl.robotcode",
        },
        trace=TraceValues.OFF,
        workspace_folders=[WorkspaceFolder(uri="file:///c%3A/tmp/robottest/dummy/testprj", name="testprj")],
        work_done_token="76db5c8a-d083-44d0-bfa8-9e004eb69a1d",
    )
