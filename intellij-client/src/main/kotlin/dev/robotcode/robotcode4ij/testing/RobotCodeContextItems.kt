package dev.robotcode.robotcode4ij.testing

/**
 * A section header row: its first cell starts with `*`, in the space-separated or the pipe-separated format, whatever
 * the language of the header.
 */
internal fun isSectionHeaderRow(line: CharSequence): Boolean {
    val text = if (line.startsWith("|")) line.drop(1).trimStart() else line
    return text.startsWith("*")
}

/**
 * The start line of the discovered test or task whose body holds the caret on [caretLine]: the greatest of
 * [startLines] at or above it, unless a section header row lies between that line and the caret. Null stands for the
 * suite of the file. [lineText] returns the text of a line of the document.
 */
internal fun enclosingTestLine(startLines: Collection<Int>, caretLine: Int, lineText: (Int) -> CharSequence): Int? {
    val start = startLines.filter { it <= caretLine }.maxOrNull() ?: return null
    return if ((start + 1..caretLine).any { isSectionHeaderRow(lineText(it)) }) null else start
}
