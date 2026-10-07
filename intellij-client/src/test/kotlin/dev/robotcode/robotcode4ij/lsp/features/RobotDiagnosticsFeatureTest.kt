package dev.robotcode.robotcode4ij.lsp.features

import com.intellij.lang.annotation.HighlightSeverity
import org.eclipse.lsp4j.Diagnostic
import org.eclipse.lsp4j.DiagnosticSeverity
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotDiagnosticsFeatureTest {

    private fun highlightSeverityOf(severity: DiagnosticSeverity?): HighlightSeverity? {
        return RobotDiagnosticsFeature().getHighlightSeverity(Diagnostic().apply { this.severity = severity })
    }

    @Test
    fun informationAndHintGetDifferentLevels() {
        assertEquals(HighlightSeverity.ERROR, highlightSeverityOf(DiagnosticSeverity.Error))
        assertEquals(HighlightSeverity.WARNING, highlightSeverityOf(DiagnosticSeverity.Warning))
        assertEquals(HighlightSeverity.WEAK_WARNING, highlightSeverityOf(DiagnosticSeverity.Information))
        assertEquals(HighlightSeverity.INFORMATION, highlightSeverityOf(DiagnosticSeverity.Hint))
    }

    @Test
    fun diagnosticWithoutSeverityIsAnError() {
        assertEquals(HighlightSeverity.ERROR, highlightSeverityOf(null))
    }
}
