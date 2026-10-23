package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.lineMarker.ExecutorAction
import com.intellij.execution.lineMarker.RunLineMarkerContributor
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.project.DumbAware
import com.intellij.psi.PsiElement
import com.intellij.util.Urls.newLocalFileUrl
import com.intellij.util.Urls.newUrl
import dev.robotcode.robotcode4ij.actions.withProfileActions
import dev.robotcode.robotcode4ij.psi.RobotSuiteFile
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.testManger

/** The kind of run marker that a discovered item gets. */
internal enum class RunMarkerKind { LEAF, SUITE }

/**
 * Tests and tasks are leaves; a suite gets a marker while it has children, and every other item gets none.
 */
internal fun runMarkerKind(item: RobotCodeTestItem): RunMarkerKind? {
    return when {
        item.type == "test" || item.type == "task" -> RunMarkerKind.LEAF
        item.type == "suite" && !item.children.isNullOrEmpty() -> RunMarkerKind.SUITE
        else -> null
    }
}

// the executors that RobotCode's runners take; others, such as PyCharm Professional's Profile and Concurrency Diagram
// in its profiler group, don't support Robot Framework runs
private val RUN_MARKER_EXECUTORS = setOf(DefaultRunExecutor.EXECUTOR_ID, DefaultDebugExecutor.EXECUTOR_ID)

/** The [gutterActions] of a run marker without the executor actions of executors other than Run and Debug. */
internal fun withRobotExecutors(gutterActions: Array<AnAction>): Array<AnAction> {
    return gutterActions.filter { it !is ExecutorAction || it.executor.id in RUN_MARKER_EXECUTORS }.toTypedArray()
}

// the markers read the discovery result, not the indexes, so they stay while the IDE indexes
class RobotCodeRunLineMarkerContributor : RunLineMarkerContributor(), DumbAware {
    override fun getInfo(element: PsiElement): Info? {
        val testElement = element.project.testManger.findTestItem(element) ?: return null
        val kind = runMarkerKind(testElement) ?: return null

        val uri = newUrl(
            "robotcode", "/", newLocalFileUrl(testElement.source!!).toString()
        ).addParameters(mapOf("line" to ((testElement.lineno ?: 1) - 1).toString()))

        val icon = getTestStateIcon(uri.toString(), element.project, kind == RunMarkerKind.SUITE)
        val info = withExecutorActions(icon)
        // running once with a profile comes after the executor actions, before "Modify Run Configuration..."
        val actions = withProfileActions(withRobotExecutors(info.actions))

        // the marker on line 1 also shows the problems that discovery reported for the file
        val problems =
            if (element is RobotSuiteFile) element.project.testManger.problems(testElement.uri ?: "") else listOf()
        if (problems.isEmpty()) {
            return Info(info.icon, actions, info.tooltipProvider)
        }
        return Info(info.icon, actions) { e ->
            (listOfNotNull(info.tooltipProvider?.apply(e)) + problems).joinToString("\n")
        }
    }

}
