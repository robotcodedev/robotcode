# Spec Delta

## ADDED Requirements

### Requirement: Home page gallery moves on by itself

The gallery next to the title of the home page SHALL move on to the next picture by itself every eight seconds, fading over to it. It SHALL NOT move on while the pointer or the keyboard focus is on it, while the enlarged view is open or while the browser tab is hidden, and not at all when the visitor's system asks for reduced motion. After the reader changes the picture, the new picture SHALL be shown for the full eight seconds.

#### Scenario: Moving on by itself
- **WHEN** a reader looks at the home page for eight seconds without touching the gallery
- **THEN** the gallery fades over to the next picture

#### Scenario: Pointer on the picture
- **WHEN** the pointer rests on the picture
- **THEN** the gallery stays on that picture

#### Scenario: Enlarged view
- **WHEN** the reader has opened the enlarged view
- **THEN** the gallery stays on the picture until the view is closed

#### Scenario: Change by hand
- **WHEN** the reader clicks the next button
- **THEN** the next picture is shown for the full eight seconds before the gallery moves on

#### Scenario: Reduced motion
- **WHEN** a visitor whose system asks for reduced motion opens the home page
- **THEN** the picture changes only when the visitor changes it
