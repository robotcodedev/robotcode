# Shop

The test data of the Markdown tests of the language server. The marker lines
of the tests are comments at column 0 inside the code blocks.

```robot
*** Variables ***
${PRICE}    10
```

Some prose between the blocks, with words like Log and ${PRICE}.

```robotframework
*** Test Cases ***
Buy Something
    Pay    ${PRICE}
#   ^^^ keyword of the file
#          ^^^^^^^^ variable of the file
    Log    done
#   ^^^ library keyword
```

More prose.

```robot
*** Keywords ***
Pay
#^^ keyword definition
    [Arguments]    ${amount}
#                  ^^^^^^^^^ argument definition
    Log    Paid ${amount}
#                 ^^^^^^^ argument
```
