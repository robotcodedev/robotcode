package dev.robotcode.robotcode4ij.lsp.features

import com.intellij.lang.annotation.HighlightSeverity
import com.redhat.devtools.lsp4ij.client.features.LSPDiagnosticFeature
import org.eclipse.lsp4j.Diagnostic
import org.eclipse.lsp4j.DiagnosticSeverity

@Suppress("UnstableApiUsage") class RobotDiagnosticsFeature : LSPDiagnosticFeature() {
    // Information diagnostics keep LSP4IJ's weak warning, which the Problems view lists. Hints get the IDE's information
    // level instead, which the Problems view does not list, so that the two levels look different.
    override fun getHighlightSeverity(diagnostic: Diagnostic): HighlightSeverity? {
        return when (diagnostic.severity) {
            DiagnosticSeverity.Hint -> {
                HighlightSeverity.INFORMATION
            }

            else -> super.getHighlightSeverity(diagnostic)
        }
    }
}
