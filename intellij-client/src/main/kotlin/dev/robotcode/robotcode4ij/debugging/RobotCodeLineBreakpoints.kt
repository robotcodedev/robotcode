package dev.robotcode.robotcode4ij.debugging

/**
 * The line breakpoints of a debug session as the debugger receives them: per file, the registered breakpoints in the
 * order they were registered and the target of Run to Cursor. A breakpoint stays under the file it was registered under
 * until it is unregistered, so that a moved breakpoint leaves nothing behind; its line is read when a list is built.
 */
internal class RobotCodeLineBreakpoints<B : Any, F : Any>(
    private val fileOf: (B) -> F?,
    private val lineOf: (B) -> Int,
) {
    /** An entry of a request list: a registered [breakpoint], or the Run to Cursor target, which has none. */
    data class Entry<B>(val line: Int, val breakpoint: B?)

    private val registered = LinkedHashMap<F, LinkedHashSet<B>>()
    private val fileByBreakpoint = HashMap<B, F>()
    private var target: Pair<F, Int>? = null
    private val idsByFile = HashMap<F, Map<Int, B?>>()

    /** The files that have or had breakpoints in this session, or the Run to Cursor target. */
    val files: Set<F>
        get() = registered.keys + listOfNotNull(target?.first)

    /** Registers [breakpoint] under its current file and returns the files whose lists changed. */
    fun register(breakpoint: B): Set<F> {
        val file = fileOf(breakpoint) ?: return emptySet()
        val previous = fileByBreakpoint.put(breakpoint, file)
        if (previous != null && previous != file) {
            registered[previous]?.remove(breakpoint)
        }
        registered.getOrPut(file) { LinkedHashSet() }.add(breakpoint)
        return setOfNotNull(previous, file)
    }

    /** The file [breakpoint] is registered under, or null if it is not registered. */
    fun registeredFile(breakpoint: B): F? = fileByBreakpoint[breakpoint]

    /** Unregisters [breakpoint] from the file it was registered under and returns that file. */
    fun unregister(breakpoint: B): Set<F> {
        val file = fileByBreakpoint.remove(breakpoint) ?: return emptySet()
        registered[file]?.remove(breakpoint)
        return setOf(file)
    }

    /** Sets the Run to Cursor target, unless a registered breakpoint is on that line, and returns whether it did. */
    fun setTarget(file: F, line: Int): Boolean {
        if (registered[file].orEmpty().any { lineOf(it) == line }) {
            return false
        }
        target = file to line
        return true
    }

    /** Clears the Run to Cursor target and returns its file, whose list changed, if there was one. */
    fun clearTarget(): F? {
        val file = target?.first
        target = null
        return file
    }

    /** The list of [file]: its registered breakpoints in registration order, then the Run to Cursor target. */
    fun entries(file: F): List<Entry<B>> = buildList {
        registered[file]?.forEach { add(Entry(lineOf(it), it)) }
        target?.takeIf { it.first == file }?.let { add(Entry(it.second, null)) }
    }

    /** Records the [ids] the debugger gave the [entries] of [file] in its answer; they replace the ids of earlier answers. */
    fun idsReceived(file: F, entries: List<Entry<B>>, ids: List<Int?>) {
        idsByFile[file] = entries.zip(ids).mapNotNull { (entry, id) -> id?.let { it to entry.breakpoint } }.toMap()
    }

    /**
     * The registered breakpoint that the debugger reported with [id] in its latest answer for its file; null for the Run
     * to Cursor target, for ids of earlier answers and for breakpoints unregistered since.
     */
    fun breakpointWithId(id: Int): B? {
        return idsByFile.values.firstNotNullOfOrNull { it[id] }?.takeIf { it in fileByBreakpoint }
    }
}
