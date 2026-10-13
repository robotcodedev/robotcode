package dev.robotcode.robotcode4ij.debugging

import org.eclipse.lsp4j.debug.Variable
import org.eclipse.lsp4j.debug.VariablesArguments
import org.eclipse.lsp4j.debug.VariablesArgumentsFilter
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

/** The number of items of a list that the Variables view shows before it offers the next page. */
internal const val VARIABLES_PAGE_SIZE = 100

/** One `variables` request: without a filter, or for the named or the indexed children, these from [start] on. */
internal data class VariablesRequest(
    val filter: VariablesArgumentsFilter? = null,
    val start: Int? = null,
    val count: Int? = null,
)

/** The requests for the children of a value or scope, and where the next page starts and how many items it has left. */
internal data class ChildrenPlan(val requests: List<VariablesRequest>, val next: Int, val remaining: Int)

/**
 * Plans the requests for the children of a value or scope from the number of indexed children the debugger reports.
 * A value with indexed children, a list, gets its named children (`len()`) with the first page and its items in pages
 * of [VARIABLES_PAGE_SIZE] from [start] on. Any other value, and a scope, gets one request without a filter: the
 * debugger then returns all of their children, and it ignores `start` for named children.
 */
internal fun planChildren(indexedVariables: Int? = null, start: Int = 0): ChildrenPlan {
    val indexed = indexedVariables ?: 0
    if (indexed <= 0) return ChildrenPlan(listOf(VariablesRequest()), 0, 0)

    val count = (indexed - start).coerceIn(0, VARIABLES_PAGE_SIZE)
    val page = VariablesRequest(VariablesArgumentsFilter.INDEXED, start, count)
    val requests = if (start == 0) listOf(VariablesRequest(VariablesArgumentsFilter.NAMED), page) else listOf(page)
    return ChildrenPlan(requests, start + count, indexed - start - count)
}

/** The children of [reference] that the requests of [plan] return, in order. */
internal suspend fun IDebugProtocolServer.children(reference: Int, plan: ChildrenPlan): List<Variable> {
    return plan.requests.flatMap { request ->
        variables(VariablesArguments().apply {
            variablesReference = reference
            filter = request.filter
            start = request.start
            count = request.count
        }).awaitRequest().variables.orEmpty().asList()
    }
}

private val PYTHON_CLASS = Regex("<class '(?:.*\\.)?([^.']*)'>")

/** The type as the debugger sends it, `<class 'robot.utils.dotdict.DotDict'>`, shortened to the class name `DotDict`. */
internal fun typeName(type: String?): String? {
    return type?.let { PYTHON_CLASS.matchEntire(it)?.groupValues?.get(1) ?: it }
}
