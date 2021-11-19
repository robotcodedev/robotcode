*** Settings ***
Library           Collections
#                 ^^^^^^^^^^^ library import by module name: re.match(r'## Library \*Collections\*.*', value)
Library           ${CURDIR}/libs/myvariables.py
#                               ^^^^^^^^^^^^^^ library import by path name: re.match(r'## Library \*myvariables.*', value)
# TODO            ^^^^^^^^^  variable in library import: value == '(builtin variable) ${CURDIR}'
Variables         ${CURDIR}/libs/myvariables.py
# TODO            ^^^^^^^^^  variable in variables import: value == '(builtin variable) ${CURDIR}'
Resource          ${CURDIR}/resources/firstresource.resource
#                                     ^^^^^^^^^^^^^^ library import by path name: re.match(r'## Resource \*firstresource.*', value)
# TODO            ^^^^^^^^^  variable in resource import: value == '(builtin variable) ${CURDIR}'

*** Variables ***
${A VAR}          i'm a var
#^^^^^^^          variable declaration: value == '(variable) ${A VAR}'
&{A DICT}         a=1    b=2    c=3
#^^^^^^^          variable declaration: value == '(variable) &{A DICT}'

*** Test Cases ***
first
    Log    Hello ${A VAR}
    Collections.Log Dictionary    ${A DICT}
#               ^^^^^^^^^^^^^^ Keyword with namespace: re.match(r'.*Log Dictionary.*', value)
# TODO  ^^^^^^^^^^^ namespace before keyword: re.match(r'.*Collections.*', value)
    FOR    ${key}    ${value}    IN    &{A DICT}
#          ^^^^^^ FOR loop variable declaration: value == '(variable) ${key}'
        Log    ${key}=${value}
#       ^^^ Keyword in FOR loop: re.match(r'.*Log.*', value)
    END
    Log    ${CMD_VAR}
#          ^^^^^^^^^^    BuiltIn variable: value == '(command line variable) ${CMD_VAR}'
#   ^^^ BuiltIn Keyword: re.match(r'.*Log.*', value)
    Log    ${CURDIR}
#          ^^^^^^^^^    BuiltIn variable: value == '(builtin variable) ${CURDIR}'
#^^^    Spaces: result is None
    Log    ${A_VAR_FROM_LIB}
# TODO         ^^^^^^^^^^^^^^^^^    variable from lib: value == '(imported variable) ${A_VAR_FROM_LIB}'


*** Keywords ***
a keyword
    Run Keyword    log    hi
#   ^^^^^^^^^^^  run keyword: re.match(r'.*Run Keyword.*', value)
#                  ^^^  run keyword argument: re.match(r'.*Log.*', value)

    Run Keywords    a simple keyword    s l e e p a w h i le
#   ^^^^^^^^^^^^  run keywords: re.match(r'.*Run Keywords.*', value)
#                   ^^^^^^^^^^^^^^^^  run keywords simple keyword: re.match(r'.*Run Keywords.*', value)
#                                       ^^^^^^^^^^^^^^^^^^^^  run keywords second parameter with spaces: re.match(r'.*sleep a while.*', value)

    Run Keywords    log  hi  AND  a simple keyword  AND  s l e e p a w h i le
#   ^^^^^^^^^^^^  run keywords: re.match(r'.*Run Keywords.*', value)
#                   ^^^  run keywords simple keyword, parameter and AND: re.match(r'.*Log.*', value)
#                                 ^^^^^^^^^^^^^^^^  run keywords simple keyword and AND: re.match(r'.*Run Keywords.*', value)
#                                                        ^^^^^^^^^^^^^^^^^^^^  run keywords second parameter with spaces and no AND: re.match(r'.*sleep a while.*', value)
#                            ^^^    AND: result is None

a simple keyword
    Pass Execution

sleep a while
    S l e e p    1s
#   ^^^^^^^^^  simple keyword with extra spaces and parameter: re.match(r'.*Sleep.*', value)
