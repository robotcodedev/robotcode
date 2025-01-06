package dev.robotcode.robotcode4ij.lsp.features

import com.intellij.lang.annotation.HighlightSeverity
import com.redhat.devtools.lsp4ij.client.features.LSPDiagnosticFeature
import org.eclipse.lsp4j.Diagnostic
import org.eclipse.lsp4j.DiagnosticSeverity

@Suppress("UnstableApiUsage") class RobotDiagnosticsFeature : LSPDiagnosticFeature() {
    override fun getHighlightSeverity(diagnostic: Diagnostic): HighlightSeverity? {
        return when (diagnostic.severity) {
            DiagnosticSeverity.Hint -> {
                HighlightSeverity.INFORMATION
            }
            
            DiagnosticSeverity.Information -> {
                HighlightSeverity.INFORMATION
            }
            
            else -> super.getHighlightSeverity(diagnostic)
        }
    }
}
