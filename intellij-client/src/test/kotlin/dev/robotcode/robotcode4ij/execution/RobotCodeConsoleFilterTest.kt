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
        "/project/results/output.xml",
        "C:\\Users\\me\\project\\results\\report.html",
        "tests/sample.robot"
    )

    private fun links(line: String) = consoleLinks(line) { it in files }.map { link ->
        Triple(line.substring(link.start, link.end), link.path, link.line)
    }

    @Test
    fun aLocationAtTheEndOfALine() {
        assertEquals(
            listOf(Triple("/project/resources/common.resource:4", "/project/resources/common.resource", 4)),
            links("    at BuiltIn.Should Be Equal (/project/resources/common.resource:4)\n")
        )
    }

    @Test
    fun pathsWithSpacesAndParentheses() {
        assertEquals(
            listOf(Triple("/home/me/my project/tests/sample.robot:7", "/home/me/my project/tests/sample.robot", 7)),
            links("    at common.Build Greeting (/home/me/my project/tests/sample.robot:7)")
        )
        // the keyword's name and the path both contain parentheses
        assertEquals(
            listOf(Triple("/home/me/copy (2)/tests/sample.robot:3", "/home/me/copy (2)/tests/sample.robot", 3)),
            links("    at Greet (Twice) (/home/me/copy (2)/tests/sample.robot:3)")
        )
    }

    @Test
    fun aWindowsPathWithADriveLetterAndBackslashes() {
        val path = "C:\\Users\\me\\project\\tests\\sample.robot"
        assertEquals(listOf(Triple("$path:12", path, 12)), links("    at common.Build Greeting ($path:12)"))
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
        assertEquals(listOf<Any>(), links("    at Keyword (tests/sample.robot:3)"))
        assertEquals(listOf<Any>(), links("Log:     tests/sample.robot"))
        // a location that does not end the line, as one inside a message
        assertEquals(listOf<Any>(), links("expected (/project/resources/common.resource:4) but got something else"))
        // a file that is not there
        assertEquals(listOf<Any>(), links("    at Keyword (/project/missing.robot:3)"))
        assertEquals(listOf<Any>(), links("Report:  /project/results/report.html"))
    }
}
