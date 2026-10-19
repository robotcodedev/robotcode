package dev.robotcode.robotcode4ij.execution

import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeConsoleFilterTest {

    // the files that exist, on whichever system the paths come from
    private val files = setOf(
        "/project/resources/common.resource",
        "/home/me/my project/tests/sample.robot",
        "/home/me/copy (2)/tests/sample.robot",
        "C:\\Users\\me\\project\\tests\\sample.robot",
        "C:\\Users\\me\\my project\\tests\\sample.robot",
        "/project/results/output.xml",
        "C:\\Users\\me\\project\\results\\report.html",
        "tests/sample.robot"
    )

    private fun links(line: String) = consoleLinks(line) { it in files }.map { link ->
        Triple(line.substring(link.start, link.end), link.path, link.line)
    }

    @Test
    fun aCallAtTheStartOfALine() {
        assertEquals(
            listOf(Triple("/project/resources/common.resource", "/project/resources/common.resource", 4)),
            links("  File \"/project/resources/common.resource\", line 4, in BuiltIn.Should Be Equal\n")
        )
    }

    @Test
    fun aLocationAtTheEndOfALine() {
        // as a log message in the results tree ends
        assertEquals(
            listOf(Triple("/project/resources/common.resource:4", "/project/resources/common.resource", 4)),
            links("Opened http://localhost:8080 as alice (/project/resources/common.resource:4)\n")
        )
    }

    @Test
    fun pathsWithSpacesAndParentheses() {
        assertEquals(
            listOf(Triple("/home/me/my project/tests/sample.robot", "/home/me/my project/tests/sample.robot", 7)),
            links("  File \"/home/me/my project/tests/sample.robot\", line 7, in common.Build Greeting")
        )
        // the path and the keyword's name both contain parentheses
        assertEquals(
            listOf(Triple("/home/me/copy (2)/tests/sample.robot", "/home/me/copy (2)/tests/sample.robot", 3)),
            links("  File \"/home/me/copy (2)/tests/sample.robot\", line 3, in Greet (Twice)")
        )
        // the message and the path at its end both contain parentheses
        assertEquals(
            listOf(Triple("/home/me/copy (2)/tests/sample.robot:3", "/home/me/copy (2)/tests/sample.robot", 3)),
            links("Greeted (twice) (/home/me/copy (2)/tests/sample.robot:3)")
        )
    }

    @Test
    fun aWindowsPathWithADriveLetterAndBackslashes() {
        val path = "C:\\Users\\me\\project\\tests\\sample.robot"
        assertEquals(listOf(Triple(path, path, 12)), links("  File \"$path\", line 12, in common.Build Greeting"))
        assertEquals(listOf(Triple("$path:12", path, 12)), links("Opened the shop ($path:12)"))
        val withSpace = "C:\\Users\\me\\my project\\tests\\sample.robot"
        assertEquals(listOf(Triple(withSpace, withSpace, 5)), links("  File \"$withSpace\", line 5, in Check Value"))
    }

    @Test
    fun theOutputFilesThatRobotFrameworkNames() {
        assertEquals(
            listOf(Triple("/project/results/output.xml", "/project/results/output.xml", null)),
            links("Output:  /project/results/output.xml\n")
        )
        val report = "C:\\Users\\me\\project\\results\\report.html"
        assertEquals(listOf(Triple(report, report, null)), links("Report:  $report"))
    }

    @Test
    fun noLinkWithoutAnExistingAbsoluteFile() {
        assertEquals(listOf<Any>(), links("Output:  NONE"))
        // a relative path, also when such a file exists relative to somewhere
        assertEquals(listOf<Any>(), links("  File \"tests/sample.robot\", line 3, in Keyword"))
        assertEquals(listOf<Any>(), links("Opened the shop (tests/sample.robot:3)"))
        assertEquals(listOf<Any>(), links("Log:     tests/sample.robot"))
        // a call that does not begin the line or a location that does not end it, as one inside a message
        assertEquals(
            listOf<Any>(),
            links("expected File \"/project/resources/common.resource\", line 4 but got something else")
        )
        assertEquals(listOf<Any>(), links("expected (/project/resources/common.resource:4) but got something else"))
        // a file that is not there
        assertEquals(listOf<Any>(), links("  File \"/project/missing.robot\", line 3, in Keyword"))
        assertEquals(listOf<Any>(), links("Opened the shop (/project/missing.robot:3)"))
        assertEquals(listOf<Any>(), links("Report:  /project/results/report.html"))
    }
}
