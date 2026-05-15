*** Settings ***
Documentation    Logs HTML messages with an embedded base64 image and an
...              external file reference, so the artifact-extraction code
...              path can be exercised by `log --extract DIR`.


*** Test Cases ***
Embedded Image Test
    Log    <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==">    HTML
    Log    Done

External File Test
    Log    See <a href="diagram.svg">diagram</a>    HTML
    Log    Done
