package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.configurations.RunProfile
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.WrappingRunConfiguration
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.testframework.AbstractTestProxy
import com.intellij.execution.testframework.actions.AbstractRerunFailedTestsAction
import com.intellij.execution.testframework.sm.runner.SMTestProxy
import com.intellij.openapi.ui.ComponentContainer
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.testManger
import java.net.URI
import java.net.URISyntaxException
import java.nio.file.FileSystemNotFoundException
import java.nio.file.InvalidPathException
import java.nio.file.Path

/** A failed test of a run's results: the file of its location, its name, and its long name in that run. */
internal data class FailedTest(val source: String?, val name: String, val longname: String?)

/**
 * The items of a "Tests and suites" target that run the [failed] tests again, with the name of the top-level suite.
 * Each test is looked up in the discovery [model] as the test with its name in the file suite of its file, and stored
 * as a gutter run stores its item; the long name of the run would not find it after a run of files and folders, whose
 * top-level suite comes from its paths. A test that discovery does not know keeps only its long name from the run.
 */
internal fun rerunSelection(
    failed: List<FailedTest>, model: Array<RobotCodeTestItem>
): Pair<String?, List<RobotRunSelectionItem>> {
    var topLevel: String? = null
    val items = failed.map { test ->
        val stored = test.source?.let { discoveredTest(model, it, test.name) }?.let { selectionItemOf(it, model) }
        if (stored != null) {
            topLevel = topLevel ?: stored.first
            stored.second
        } else {
            RobotRunSelectionItem().apply {
                kind = "test"
                name = test.longname ?: test.name
            }
        }
    }
    return topLevel to items
}

// the test or task with [name] in the file suite of the file at [source]
private fun discoveredTest(model: Array<RobotCodeTestItem>, source: String, name: String): RobotCodeTestItem? {
    val file = pathOf { Path.of(source) } ?: return null
    fun search(items: Array<RobotCodeTestItem>): RobotCodeTestItem? = items.firstNotNullOfOrNull { item ->
        val inFile = item.type == "suite" && item.uri?.let { uri -> pathOf { Path.of(URI(uri)) } } == file
        if (inFile) {
            item.children?.firstOrNull { (it.type == "test" || it.type == "task") && it.name == name }
        } else {
            search(item.children ?: arrayOf())
        }
    }
    return search(model)
}

private fun pathOf(path: () -> Path): Path? = try {
    path()
} catch (_: InvalidPathException) {
    null
} catch (_: URISyntaxException) {
    null
} catch (_: IllegalArgumentException) {
    null
} catch (_: FileSystemNotFoundException) {
    null
}

/** The failed tests among the [proxies] of the results tree, without the suites. */
internal fun failedTestsOf(proxies: List<AbstractTestProxy>): List<FailedTest> =
    proxies.filterIsInstance<SMTestProxy>().filter { !it.isSuite }.map { proxy ->
        FailedTest(proxy.locationUrl?.let(::resultSourcePath), proxy.name, proxy.metainfo)
    }

/**
 * A copy of [configuration] whose "Tests and suites" target holds the [failed] tests, as found in the discovery
 * [model].
 */
internal fun rerunConfiguration(
    configuration: RobotCodeRunConfiguration, failed: List<FailedTest>, model: Array<RobotCodeTestItem>
): RobotCodeRunConfiguration {
    val (topLevel, items) = rerunSelection(failed, model)
    val copy = configuration.clone() as RobotCodeRunConfiguration
    copy.options.targetKind = RobotRunTargetKind.SELECTION
    copy.options.selection = items.toMutableList()
    copy.options.topLevelSuite = topLevel
    return copy
}

/** A Robot Framework run configuration, or the wrapper around one in which the platform reruns failed tests. */
internal fun isRobotRunProfile(profile: RunProfile): Boolean =
    profile is RobotCodeRunConfiguration || (profile as? WrappingRunConfiguration<*>)?.peer is RobotCodeRunConfiguration

/**
 * Runs the failed tests of a run again, in the same tab and with the same executor: a copy of the run's
 * [configuration] whose target holds them. The copy brings its own console properties, so the next rerun starts from
 * it and narrows down to the tests that still fail.
 */
internal class RobotCodeRerunFailedTestsAction(
    container: ComponentContainer, private val configuration: RobotCodeRunConfiguration
) : AbstractRerunFailedTestsAction(container) {

    override fun getRunProfile(environment: ExecutionEnvironment): MyRunProfile {
        val project = configuration.project
        val copy = rerunConfiguration(
            configuration, failedTestsOf(getFailedTests(project)), project.testManger.testItems
        )
        return object : MyRunProfile(copy) {
            override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState =
                copy.getState(executor, environment)
        }
    }
}
