# Spec Delta

## ADDED Requirements

### Requirement: Images in documentation

A viewer SHALL show the images that the documentation on its page references by the path of a local file. This applies to Robot Framework's documentation syntax and, in Markdown documentation, to images, reference-style images and `<img>` elements. Images in the documentation of keywords SHALL be included.

#### Scenario: Image in the workspace folder's root
- **WHEN** the resource file `resources/global/WebUI.resource` documents `[images/doc/WebUI_global.png|WebUI Global]`, the file `images/doc/WebUI_global.png` exists in the root of the viewer's workspace folder, and a viewer shows the resource file
- **THEN** the page shows the image

#### Scenario: Markdown documentation
- **WHEN** a library documented in Markdown format on Robot Framework 7.5 contains `![Logo](pics/logo.png)`, `![Logo][logo]` with `[logo]: pics/logo.png`, and `<img src="pics/logo.png">`, and `pics/logo.png` lies beside the library
- **THEN** the page shows the image in all three places

#### Scenario: Path with spaces
- **WHEN** a resource file documents `[images/doc/my image.png|My image]` and `images/doc/my image.png` exists in the root of the workspace folder
- **THEN** the page shows the image

#### Scenario: Image in a keyword's documentation
- **WHEN** the documentation of a keyword of a resource file contains `[pics/step.png|Step]`, and `pics/step.png` lies beside the resource file
- **THEN** the page shows the image in the keyword's documentation

### Requirement: Where a viewer looks up an image

A relative image path SHALL be looked up first relative to the file that the documentation comes from, then relative to the root of the viewer's workspace folder. The first file that exists SHALL be shown. That file is the library or resource file, and for a keyword's documentation, the file that defines the keyword. A path that starts with `/` SHALL be looked up only relative to the root of the workspace folder.

#### Scenario: Image beside the resource file
- **WHEN** `resources/global/WebUI.resource` documents `[pics/logo.png|Logo]` and `resources/global/pics/logo.png` exists
- **THEN** the page shows that image

#### Scenario: The closer image wins
- **WHEN** `resources/global/WebUI.resource` documents `[images/doc/both.png|Both]`, and both `resources/global/images/doc/both.png` and `images/doc/both.png` in the root of the workspace folder exist
- **THEN** the page shows `resources/global/images/doc/both.png`

#### Scenario: Path from the root
- **WHEN** `resources/global/WebUI.resource` documents `[/images/doc/logo.png|Logo]` and `[/pics/logo.png|Beside]`, and `images/doc/logo.png` exists in the root of the workspace folder, while `pics/logo.png` exists only beside the resource file
- **THEN** the page shows the first image, and not the second

#### Scenario: Keyword in another module of a library
- **WHEN** a library package documents the keyword `Open Page`, which is defined in its module `keywords/pages.py`, with `[pics/page.png|Page]`, and `pics/page.png` lies beside `keywords/pages.py`
- **THEN** the page shows that image in the documentation of `Open Page`

#### Scenario: Library outside the workspace folder
- **WHEN** a library in a virtual environment outside the workspace folder documents `[images/doc/logo.png|Logo]`, and the file exists only in the root of the workspace folder
- **THEN** the page shows the image from the root of the workspace folder

#### Scenario: Several workspace folders
- **WHEN** two workspace folders each contain `images/doc/logo.png`, and a viewer of the second folder shows a resource file of that folder that documents `[images/doc/logo.png|Logo]`
- **THEN** the page shows the image of the second folder

### Requirement: Which image files a viewer shows

Relative to a file inside the viewer's workspace folder, a path MAY go up with `..`, but the image SHALL be shown only if it lies inside the folder. Relative to a file outside the folder, only images in that file's folder and below SHALL be shown. Relative to the root of the folder, only images inside the folder SHALL be shown. Paths with a drive letter or a backslash SHALL NOT be looked up on any platform. `https:` images SHALL be shown, `http:` images SHALL NOT.

#### Scenario: Up inside the workspace folder
- **WHEN** `resources/global/WebUI.resource` documents `[../images/up.png|Up]` and `resources/images/up.png` exists
- **THEN** the page shows the image

#### Scenario: Up out of the workspace folder
- **WHEN** a resource file inside the workspace folder documents a path with `..` that leads to an image outside the folder
- **THEN** the page does not show the image

#### Scenario: Library outside the workspace folder
- **WHEN** a library in a virtual environment outside the workspace folder documents `[pics/logo.png|Beside]` and `[../shared/logo.png|Up]`, and both files exist
- **THEN** the page shows the first image, and not the second

#### Scenario: Drive letters and backslashes
- **WHEN** documentation contains `[C:/images/logo.png|Drive]` or `[images\doc\logo.png|Backslash]`, also on Windows, and the files exist
- **THEN** the page does not show these images

#### Scenario: Images from the web
- **WHEN** documentation contains an image with an `https:` URL and one with an `http:` URL
- **THEN** the page shows the `https:` image and not the `http:` image

#### Scenario: Missing file
- **WHEN** documentation references an image whose file exists neither beside the documented file nor in the root of the workspace folder
- **THEN** the page does not show that image and shows the rest of the documentation as usual

### Requirement: Images keep the viewer and the page's Markdown

Showing the images of a page SHALL NOT reload the viewer: its find bar, outline and history SHALL stay as they are for a page without images. *Open as Markdown* SHALL keep the image paths as the documentation writes them. Images SHALL be shown in remote windows as they are in a local window.

#### Scenario: Find bar stays open
- **WHEN** the find bar of a viewer is open and the user follows a link to a page with images
- **THEN** the find bar stays open with its text and shows the matches of the new page

#### Scenario: Markdown keeps the paths
- **WHEN** a viewer shows `resources/global/WebUI.resource` with the image `[images/doc/WebUI_global.png|WebUI Global]`, and the user chooses "Open as Markdown"
- **THEN** the document contains `![WebUI Global](images/doc/WebUI_global.png)`

#### Scenario: Remote window
- **WHEN** a viewer in a window connected to SSH, WSL or a dev container shows a resource file with an image beside it
- **THEN** the page shows the image as in a local window
