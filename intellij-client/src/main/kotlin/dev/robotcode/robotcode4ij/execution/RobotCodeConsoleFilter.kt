package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.filters.Filter
import com.intellij.execution.filters.HyperlinkInfo
import com.intellij.execution.filters.LazyFileHyperlinkInfo
import com.intellij.execution.filters.OpenFileHyperlinkInfo
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.io.FileUtil
import com.intellij.openapi.vfs.LocalFileSystem
import java.nio.file.Files
import java.nio.file.InvalidPathException
import java.nio.file.Path

/** A link in a console line from [start] to [end] that opens [path], at [line] for a location. */
internal data class ConsoleLink(val start: Int, val end: Int, val path: String, val line: Int? = null)

// a call `File "<path>", line <line>` that begins a line, as Python lists the calls of a traceback and the stack trace
// of a failure lists them; the quotes delimit the path, which may contain spaces
private val CALL = Regex("""^\s*File "([^"]+)", line (\d+)""")

// the end of a location `(<path>:<line>)`, as each log message in the results tree ends
private val LOCATION_END = Regex(""":(\d+)\)\s*$""")

// a line in which Robot Framework names an output file
private val OUTPUT_FILE = Regex("""^(?:Output|Log|Report|XUnit|Debug):\s+(\S.*?)\s*$""")

// an absolute path of POSIX or of Windows, whichever system the console runs on
private val ABSOLUTE_PATH = Regex("""^(?:/|[A-Za-z]:[\\/]|\\\\)""")

/**
 * The links in a console [line]: the path of a call `File "<path>", line <line>` that begins the line, with its line;
 * the path and line of a location `(<path>:<line>)` that ends the line; or the path in a line in which Robot Framework
 * names an output file; only for an absolute path of a file that [isFile] confirms, so `NONE` stays text. A path at the
 * end of a line may contain spaces and parentheses, so that location tries each opening parenthesis from the right.
 */
internal fun consoleLinks(line: String, isFile: (String) -> Boolean): List<ConsoleLink> {
    fun linkable(path: String) = ABSOLUTE_PATH.containsMatchIn(path) && isFile(path)

    OUTPUT_FILE.find(line)?.let { match ->
        val path = match.groups[1] ?: return listOf()
        if (!linkable(path.value)) return listOf()
        return listOf(ConsoleLink(path.range.first, path.range.last + 1, path.value))
    }
    CALL.find(line)?.let { call ->
        val path = call.groups[1] ?: return listOf()
        val number = call.groupValues[2].toIntOrNull() ?: return listOf()
        if (!linkable(path.value)) return listOf()
        return listOf(ConsoleLink(path.range.first, path.range.last + 1, path.value, number))
    }
    val end = LOCATION_END.find(line) ?: return listOf()
    val number = end.groupValues[1].toIntOrNull() ?: return listOf()
    var open = line.lastIndexOf('(', end.range.first)
    while (open >= 0) {
        val path = line.substring(open + 1, end.range.first)
        if (linkable(path)) {
            return listOf(ConsoleLink(open + 1, end.range.first + 1 + end.groupValues[1].length, path, number))
        }
        open = line.lastIndexOf('(', open - 1)
    }
    return listOf()
}

/**
 * Makes the links of a Robot Framework run in its console and in the stack traces of its failures: a location opens
 * its file at its line, a report or log where "Open output target" says, as Open Report and Open Log do, and any other
 * output file in the editor.
 */
class RobotCodeConsoleFilter(private val project: Project) : Filter, DumbAware {
    override fun applyFilter(line: String, entireLength: Int): Filter.Result? {
        val offset = entireLength - line.length

        // the disk decides, because the IDE learns of the files that a run just wrote only after its last lines; an
        // output file is looked up when it is clicked, a location's source file is known
        val items = consoleLinks(line, ::isRegularFile).mapNotNull { link ->
            val path = FileUtil.toSystemIndependentName(link.path)
            val info = when {
                link.line != null -> {
                    val file = LocalFileSystem.getInstance().findFileByPath(path) ?: return@mapNotNull null
                    OpenFileHyperlinkInfo(project, file, link.line - 1)
                }
                path.endsWith(".html", ignoreCase = true) ->
                    HyperlinkInfo { openOutputFileInTarget(it, Path.of(link.path)) }
                else -> LazyFileHyperlinkInfo(project, path, 0, 0)
            }
            Filter.ResultItem(offset + link.start, offset + link.end, info)
        }
        return if (items.isEmpty()) null else Filter.Result(items)
    }

    private fun isRegularFile(path: String): Boolean = try {
        Files.isRegularFile(Path.of(path))
    } catch (_: InvalidPathException) {
        false
    }
}
