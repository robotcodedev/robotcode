package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.process.ProcessOutputType
import com.intellij.execution.process.ProcessOutputTypes
import com.intellij.execution.testframework.sm.runner.OutputToGeneralTestEventsConverter
import com.intellij.execution.testframework.sm.runner.events.TestFailedEvent
import com.intellij.execution.testframework.sm.runner.events.TestFinishedEvent
import com.intellij.execution.testframework.sm.runner.events.TestIgnoredEvent
import com.intellij.execution.testframework.sm.runner.events.TestOutputEvent
import com.intellij.execution.testframework.sm.runner.events.TestStartedEvent
import com.intellij.execution.testframework.sm.runner.events.TestSuiteFinishedEvent
import com.intellij.execution.testframework.sm.runner.events.TestSuiteStartedEvent
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.util.Key
import com.intellij.util.Urls.newLocalFileUrl
import com.intellij.util.Urls.newUrl
import com.jetbrains.rd.util.lifetime.LifetimeDefinition
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProtocolClient
import dev.robotcode.robotcode4ij.debugging.RobotEnqueuedArguments
import dev.robotcode.robotcode4ij.debugging.RobotExecutionEventArguments
import org.eclipse.lsp4j.debug.OutputEventArguments
import org.eclipse.lsp4j.debug.OutputEventArgumentsCategory
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

// the id of the results tree's root node
private const val ROOT_ID = "0"

/**
 * Turns a Robot Framework run into the results tree of the run tab. Robot Framework's events come from the
 * [debugClient], the output of the process through [process]. Both reach the platform's events processor under one
 * lock and in the order they were written: before a debugger event is applied, [awaitOutput] waits until the process
 * output written before it has arrived. Nothing reaches the processor before the platform has started the tree, and
 * nothing after it has finished it.
 */
class RobotOutputToGeneralTestEventsConverter(
    testFrameworkName: String,
    debugClient: RobotCodeDebugProtocolClient?,
    private val awaitOutput: () -> Unit,
) : OutputToGeneralTestEventsConverter(testFrameworkName, false, false, false) {

    private val lock = ReentrantLock()
    private val subscriptions = LifetimeDefinition()
    private val queued = mutableListOf<() -> Unit>()
    private var started = false
    private var finished = false

    // the ids of the running suites and tests, the innermost last
    private val runningIds = mutableListOf<String>()

    init {
        debugClient?.onRobotEnqueued?.advise(subscriptions) { args -> applyAfterOutput { robotEnqueued(args) } }
        debugClient?.onRobotStarted?.advise(subscriptions) { args -> applyAfterOutput { robotStarted(args) } }
        debugClient?.onRobotEnded?.advise(subscriptions) { args -> applyAfterOutput { robotEnded(args) } }
        debugClient?.onRobotSetFailed?.advise(subscriptions) { args -> applyAfterOutput { robotSetFailed(args) } }
        debugClient?.onOutput?.advise(subscriptions) { args -> applyAfterOutput { output(args) } }
    }

    // the wait happens outside the lock, because the output readers deliver their text through it
    private fun applyAfterOutput(item: () -> Unit) {
        awaitOutput()
        apply(item, queueBeforeStart = true)
    }

    // before the start, process text such as the command line goes to the processor at once, as long as no debugger
    // event waits for the start; after one does, the text waits behind it, so that the order stays the same
    private fun apply(item: () -> Unit, queueBeforeStart: Boolean) {
        lock.withLock {
            when {
                finished -> Unit
                started -> item()
                queueBeforeStart || queued.isNotEmpty() -> queued.add(item)
                else -> item()
            }
        }
    }

    override fun startTesting() {
        super.startTesting()
        lock.withLock {
            started = true
            queued.forEach { it() }
            queued.clear()
        }
    }

    override fun finishTesting() {
        lock.withLock {
            finished = true
            queued.clear()
        }
        super.finishTesting()
    }

    // the text goes to the results as it arrives, without waiting for the end of its line
    override fun process(text: String, outputType: Key<*>) {
        apply({ processOutput(text, outputType) }, queueBeforeStart = false)
    }

    override fun dispose() {
        subscriptions.terminate()
        super.dispose()
    }

    private fun locationUrl(args: RobotExecutionEventArguments): String? {
        val source = args.attributes.source ?: return null
        return newUrl("robotcode", "/", newLocalFileUrl(source).toString())
            .addParameters(mapOf("line" to ((args.attributes.lineno ?: 1) - 1).toString())).toString()
    }

    private fun duration(args: RobotExecutionEventArguments): Long = (args.attributes.elapsedtime ?: 0).toLong()

    // the listener announces the run's tests once, when the first suite starts, so the progress has its total
    private fun robotEnqueued(args: RobotEnqueuedArguments) {
        processor?.onTestsCountInSuite(enqueuedTestCount(args.items))
    }

    private fun robotStarted(args: RobotExecutionEventArguments) {
        runningIds.add(args.id)
        val processor = processor ?: return
        val parentId = args.parentId ?: ROOT_ID
        val url = locationUrl(args)
        // the full name, with which RobotSMTestLocator finds the item again after lines moved
        val metainfo = args.attributes.longname
        when (args.type) {
            "suite" -> processor.onSuiteStarted(
                TestSuiteStartedEvent(args.name, args.id, parentId, url, metainfo, null, null, true)
            )
            "test" -> processor.onTestStarted(
                TestStartedEvent(args.name, args.id, parentId, url, metainfo, null, null, true)
            )
        }
    }

    private fun robotEnded(args: RobotExecutionEventArguments) {
        val lastId = runningIds.removeLastOrNull()
        if (lastId != args.id) {
            thisLogger().warn("Test item ID stack is out of sync. Expected $lastId, got ${args.id}")
        }
        val processor = processor ?: return
        when (args.type) {
            "suite" -> processor.onSuiteFinished(TestSuiteFinishedEvent(args.name, args.id))
            "test" -> when (args.attributes.status) {
                "PASS" -> processor.onTestFinished(TestFinishedEvent(args.name, args.id, duration(args)))
                "SKIP" -> processor.onTestIgnored(
                    TestIgnoredEvent(args.name, args.id, args.attributes.message ?: "Skipped", null)
                )
                else -> processor.onTestFailure(failure(args, args.attributes.message ?: "Error", duration(args)))
            }
        }
    }

    // the failed keywords as the stack trace, whose first location is where navigating from the test goes
    private fun failure(args: RobotExecutionEventArguments, message: String, duration: Long) = TestFailedEvent(
        args.name, args.id, message, failureStackTrace(args.failedKeywords), false, null, null, null, null, false,
        false, duration
    )

    // a failed or skipped suite teardown marks the suite's tests again, also tests that passed
    private fun robotSetFailed(args: RobotExecutionEventArguments) {
        val processor = processor ?: return
        val message = args.attributes.message ?: ""
        when (args.attributes.status) {
            "FAIL" -> processor.onTestFailure(failure(args, message, -1))
            "SKIP" -> processor.onTestIgnored(TestIgnoredEvent(args.name, args.id, message, null))
        }
    }

    // the output of the process belongs to the innermost running suite or test, as the debugger's output does; as
    // uncaptured output, the platform would give it to any running suite, not necessarily the innermost one
    private fun processOutput(text: String, outputType: Key<*>) {
        val processor = processor ?: return
        val id = runningIds.lastOrNull()
        if (id == null || outputType == ProcessOutputTypes.SYSTEM) {
            processor.onUncapturedOutput(text, outputType)
            return
        }
        // the event has no colors of its own, so the colors that Robot Framework writes with console colors on go into
        // the text
        val color = (outputType as? ProcessOutputType)?.escapeSequence ?: ""
        processor.onTestOutput(TestOutputEvent("", id, color + text, !ProcessOutputType.isStderr(outputType)))
    }

    // log messages and other debugger output belong to the innermost running suite or test
    private fun output(args: OutputEventArguments) {
        val processor = processor ?: return
        processor.onTestOutput(
            TestOutputEvent(
                args.category ?: OutputEventArgumentsCategory.CONSOLE,
                runningIds.lastOrNull() ?: ROOT_ID,
                "\u001b[38;5;243m${args.output}\u001b[0m",
                args.category != OutputEventArgumentsCategory.STDERR
            )
        )
    }
}
