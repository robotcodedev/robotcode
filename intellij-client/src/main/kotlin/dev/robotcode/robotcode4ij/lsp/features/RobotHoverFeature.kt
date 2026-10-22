package dev.robotcode.robotcode4ij.lsp.features

import com.intellij.psi.PsiFile
import com.redhat.devtools.lsp4ij.client.features.LSPHoverFeature
import org.eclipse.lsp4j.MarkupContent

/**
 * Puts the HTML that LSP4IJ converts from the language server's Markdown hover into an `<html>` element.
 *
 * LSP4IJ 0.21.0 passes this HTML to the Ctrl+hover hint without that element. The hint then takes it for text and turns
 * every line break into `<br>` (`UIUtil.getHtmlBody`), which leaves a large gap in front of tables and an empty line
 * after each heading and paragraph. Quick Documentation and the hover remove the element again. Remove this class once
 * LSP4IJ adds the element itself.
 */
@Suppress("UnstableApiUsage") class RobotHoverFeature : LSPHoverFeature() {
    override fun convertMarkDownToHtml(content: MarkupContent, file: PsiFile): String? =
        super.convertMarkDownToHtml(content, file)?.let { "<html>$it</html>" }
}
