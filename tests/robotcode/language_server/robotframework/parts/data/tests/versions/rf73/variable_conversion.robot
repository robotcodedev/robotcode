*** Variables ***
${a: int}                           1
${s: str}                           hallo welt
${k: Literal["Yes", "No"]}          No
@{numbers: int}                     1    2    4    11
@{wrong_numbers: int}               1    2    4    11aa
${time: datetime}                   now
${DATES: list[date]}                {'rc1': '2025-05-08', 'final': '2025-05-30'}
${PRIORITIES: dict[int, str]}       {3278: 'Critical', 4173: 'High', 5334: 'High'}


*** Test Cases ***
suite variables
    Log    ${a}
    Log    ${s}
    Log    ${k}
    Log    ${time}
    Log    ${numbers}
    Log    ${TYPE_VAR}: ${{type($TYPE_VAR)}}
    a simple keyword with args    2    a string    [1,2,3]
    a simple keyword with default arguments
    a simple keyword with union argument    1
    a simple keyword with union argument    Hallo Welt
    a simple keyword with union argument    ${None}

local variables
    VAR    ${i: int}    1234
    VAR    ${u: int | str}    1234
    Log    ${i}
    Log    ${u}

keyword assignments
    ${i: int}    Evaluate    1+2
    Log    ${i}

for loops
    VAR    ${i}    1

    FOR    ${l: int}    IN RANGE    1    100
        Log    ${l}
    END

    FOR    ${i: int}    ${s: str}    IN ENUMERATE    arg    arg1
        Log    ${i} ${s}
    END

if assignment
    ${a: int}    IF    $a    Evaluate    "asd"    ELSE    Evaluate    3+4
    Log    ${a}

calling kws with embedded args
    a keyword with embedded args
    a testcase with embedded args


*** Keywords ***
a simple keyword with args
    [Arguments]    ${a: int}    ${c: str}    ${d: list[str]}
    VAR    ${a}    1    scope=TEST
    Log    ${a}
    Log    ${c}
    Log    ${d}
    Log    ${}

a simple keyword with default arguments
    [Arguments]    ${a}=1    ${b: int}=1
    Log    ${a}
    Log    ${b}

a simple keyword with union argument
    [Arguments]    ${a: int | str | None}
    Log    ${a}

# TODO see here https://github.com/robotframework/robotframework/issues/5443
# a simple keyword Non-default argument after default arguments
#    [Arguments]    ${a}=1    ${b: int}
#    Log    ${a}
#    Log    ${b}

# Varargs
#    [Arguments]    @{v: int}    @{w}
#    Whatever

a ${keyword: int:keyword|testcase} with embedded args
    [Documentation]    this is a simple embedded keyword
    Log    ${keyword}
