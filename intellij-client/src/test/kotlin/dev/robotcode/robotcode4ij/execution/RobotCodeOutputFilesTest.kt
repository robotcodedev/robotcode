package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.debugging.RobotExitedEventArguments
import dev.robotcode.robotcode4ij.execution.RobotOpenOutputTarget.BROWSER
import dev.robotcode.robotcode4ij.execution.RobotOpenOutputTarget.BUILT_IN_PREVIEW
import dev.robotcode.robotcode4ij.execution.RobotOpenOutputTarget.DEFAULT_BROWSER
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.nio.file.Path

class RobotCodeOutputFilesTest {

    private val exited = RobotExitedEventArguments(
        reportFile = "results/report.html", logFile = "results/log.html", outputFile = "results/output.xml",
        exitCode = 0
    )

    private val written = setOf(Path.of("results/report.html"), Path.of("results/log.html"))

    private fun fileFor(kind: RobotOpenOutput, exited: RobotExitedEventArguments?, existing: Set<Path> = written) =
        reportedOutputFile(kind, exited) { it in existing }

    @Test
    fun theChosenFileOfTheRunOpens() {
        assertEquals(Path.of("results/report.html"), fileFor(RobotOpenOutput.REPORT, exited))
        assertEquals(Path.of("results/log.html"), fileFor(RobotOpenOutput.LOG, exited))
    }

    @Test
    fun nothingOpensWhenNothingIsChosen() {
        assertNull(fileFor(RobotOpenOutput.NONE, exited))
    }

    @Test
    fun nothingOpensBeforeTheRunReportedItsFiles() {
        assertNull(fileFor(RobotOpenOutput.REPORT, null))
    }

    @Test
    fun nothingOpensForAFileThatTheRunDidNotWrite() {
        // `--log NONE`: Robot Framework reports no log
        assertNull(fileFor(RobotOpenOutput.LOG, exited.copy(logFile = null)))
        // reported, but no longer there
        assertNull(fileFor(RobotOpenOutput.REPORT, exited, existing = setOf()))
    }

    @Test
    fun theDefaultBrowserStandsInForATargetThatIsNotThere() {
        // the target of the Run page, JCEF, the stored browser active, the target the file opens in
        val cases = listOf(
            listOf(BUILT_IN_PREVIEW, true, false, BUILT_IN_PREVIEW),
            listOf(BUILT_IN_PREVIEW, false, false, DEFAULT_BROWSER),
            listOf(DEFAULT_BROWSER, true, false, DEFAULT_BROWSER),
            listOf(DEFAULT_BROWSER, false, true, DEFAULT_BROWSER),
            listOf(BROWSER, true, true, BROWSER),
            listOf(BROWSER, false, true, BROWSER),
            listOf(BROWSER, true, false, DEFAULT_BROWSER)
        )
        for ((target, previewSupported, browserActive, expected) in cases) {
            assertEquals(
                "$target, JCEF $previewSupported, browser active $browserActive", expected,
                effectiveOutputTarget(
                    target as RobotOpenOutputTarget, previewSupported as Boolean, browserActive as Boolean
                )
            )
        }
    }
}
