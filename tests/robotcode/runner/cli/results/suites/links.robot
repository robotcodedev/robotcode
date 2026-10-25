*** Settings ***
Documentation    Logs file references, media and embedded files the way
...              SeleniumLibrary, Browser and OperatingSystem do, so that
...              `log --extract DIR` can be checked against them. Linked
...              files go next to the result file, as relative links are
...              resolved against its folder.
Library          OperatingSystem


*** Test Cases ***
File References
    # SeleniumLibrary links a screenshot named after a test encoded, as Robot Framework's `get_link_path` does.
    Write File Next To Output    My Test-1.png
    Log    <a href="My%20Test-1.png"><img src="My%20Test-1.png" width="800px"></a>    HTML
    Write File Next To Output    selenium-screenshot-1.png
    Log    </td></tr><tr><td colspan="3"><a href="selenium-screenshot-1.png"><img src="selenium-screenshot-1.png" width="800px"></a>    HTML
    Write File Next To Output    notes.txt
    Log    <a href="notes.txt#part">notes</a>    HTML
    # OperatingSystem links `file://` and the path as it is.
    ${dir}=    Output Folder
    Create File    ${dir}/my data.csv    a,b\n
    Create File    ${TEMPDIR}/robotcode-links-outside.txt    x
    Create Directory    ${dir}/downloads
    Log    <img src="../shot.png">    HTML
    Write File Next To Output    thumb.png
    Write File Next To Output    full.png
    Log    <a href="full.png"><img src="thumb.png"></a>    HTML
    [Teardown]    Remove File    ${TEMPDIR}/robotcode-links-outside.txt

Media
    # Browser logs the video of a closed context with the table-row prefix and an encoded name.
    Write File Next To Output    clip@1.webm
    Log    </td></tr><tr><td colspan="3"><video width="1280" height="720" controls><source src="clip%401.webm" type="video/webm"></video>    HTML
    Write File Next To Output    sound.mp3
    Log    <audio src="sound.mp3" controls></audio>    HTML

Embedded Files
    # The `download` attribute of a link names the file it embeds.
    Log    <a href="data:text/plain;base64,SGVsbG8gd29ybGQK" download="hello.txt">hello.txt</a>    HTML
    Log    <a href="data:text/plain;base64,U2Vjb25kCg==" download="hello.txt">hello.txt</a>    HTML
    Log    <a href="data:text/plain;base64,RXZpbAo=" download="../../evil.txt">evil</a>    HTML
    Log    <a href="data:text/plain;base64,RG90cwo=" download="..">dots</a>    HTML
    Log    <a href="data:text/plain;base64,Q29uCg==" download="con.txt">con</a>    HTML

Repeated References
    # A file, an embedded image and a missing file, each referenced by two messages.
    ${dir}=    Output Folder
    Create File    ${dir}/data.csv    a,b\n
    Log    See <a href="data.csv">data.csv</a>    HTML
    Log    <img alt="pixel" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==">    HTML
    Log    Again: <img alt="pixel" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==">    HTML
    Log    <a href="missing.txt">missing</a>    HTML
    Log    Again: <a href="missing.txt">missing</a>    HTML


*** Keywords ***
Output Folder
    [Documentation]    The folder of the result file, against which relative links are resolved.
    ${dir}    ${_}=    Split Path    ${OUTPUT FILE}
    RETURN    ${dir}

Write File Next To Output
    [Documentation]    Writes a file without logging a link to it, as the screenshot keywords of the libraries do.
    [Arguments]    ${name}
    ${dir}=    Output Folder
    Evaluate    pathlib.Path(r'''${dir}''', r'''${name}''').write_bytes(b'x')    modules=pathlib
