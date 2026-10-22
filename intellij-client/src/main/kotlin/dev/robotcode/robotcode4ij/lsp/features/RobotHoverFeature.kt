package dev.robotcode.robotcode4ij.lsp.features

import com.intellij.psi.PsiFile
import com.redhat.devtools.lsp4ij.client.features.LSPHoverFeature
import org.eclipse.lsp4j.MarkupContent

// the header of a table whose cells are all empty; the language server writes one above the arguments of a keyword and
// above the version and scope of a library or resource file, because a Markdown table needs a header
private val EMPTY_TABLE_HEADER = Regex("""<thead>\s*<tr>(?:\s*<th[^>]*>\s*</th>)*\s*</tr>\s*</thead>\s*""")

/**
 * Adjusts the HTML that LSP4IJ converts from the language server's Markdown hover.
 *
 * It removes the header of a table when all of its cells are empty. The documentation shows such a header as a large
 * gap between a heading such as "Arguments:" and the table.
 *
 * It also puts the HTML into an `<html>` element. LSP4IJ 0.21.0 passes this HTML to the Ctrl+hover hint without that
 * element. The hint then takes it for text and turns every line break into `<br>` (`UIUtil.getHtmlBody`), which leaves
 * a large gap in front of tables and an empty line after each heading and paragraph. Quick Documentation and the hover
 * remove the element again. Drop the element once LSP4IJ adds it itself.
 */
@Suppress("UnstableApiUsage") class RobotHoverFeature : LSPHoverFeature() {
    override fun convertMarkDownToHtml(content: MarkupContent, file: PsiFile): String? =
        super.convertMarkDownToHtml(content, file)?.let { "<html>${it.replace(EMPTY_TABLE_HEADER, "")}</html>" }
}
