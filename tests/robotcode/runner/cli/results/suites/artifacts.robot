*** Settings ***
Documentation    Logs HTML messages with an embedded base64 image, an
...              external file reference and screenshot messages like those
...              of SeleniumLibrary and Browser, so the artifact-extraction
...              code path can be exercised by `log --extract DIR`.
Library          OperatingSystem


*** Test Cases ***
Embedded Image Test
    Log    <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==">    HTML
    Log    Done

External File Test
    Log    See <a href="diagram.svg">diagram</a>    HTML
    Log    Done

Screenshot Test
    # SeleniumLibrary and Browser start every screenshot message with markup that closes the table row of log.html.
    # Relative links are resolved against the folder of the result file, so the screenshot goes next to it. It is
    # not written with `Create File`, whose own `file://` link would be another artefact of this test.
    ${dir}    ${_}=    Split Path    ${OUTPUT FILE}
    Evaluate    pathlib.Path(r'''${dir}''', 'screenshot-1.png').write_bytes(b'png')    modules=pathlib
    Log    </td></tr><tr><td colspan="3"><a href="screenshot-1.png"><img src="screenshot-1.png" width="800px"></a>    HTML
    Log    </td></tr><tr><td colspan="3"><img alt="screenshot" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==" width="800px">    HTML
