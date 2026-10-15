package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.filters.HyperlinkInfo
import com.intellij.execution.process.ProcessOutputType
import com.intellij.execution.process.ProcessOutputTypes
import com.intellij.execution.testframework.Printable
import com.intellij.execution.testframework.Printer
import com.intellij.execution.testframework.sm.runner.GeneralIdBasedToSMTRunnerEventsConvertor
import com.intellij.execution.testframework.sm.runner.GeneralTestEventsProcessor
import com.intellij.execution.testframework.sm.runner.SMTestProxy
import com.intellij.execution.testframework.sm.runner.TestProxyPrinterProvider
import com.intellij.execution.testframework.sm.runner.events.TestFailedEvent
import com.intellij.execution.testframework.sm.runner.events.TestFinishedEvent
import com.intellij.execution.testframework.sm.runner.events.TestIgnoredEvent
import com.intellij.execution.testframework.sm.runner.events.TestOutputEvent
import com.intellij.execution.testframework.sm.runner.events.TestStartedEvent
import com.intellij.execution.testframework.sm.runner.events.TestSuiteFinishedEvent
import com.intellij.execution.testframework.sm.runner.events.TestSuiteStartedEvent
import com.intellij.execution.testframework.sm.runner.states.TestStateInfo
import com.intellij.execution.ui.ConsoleViewContentType
import com.intellij.openapi.util.Key
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.util.Urls
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProtocolClient
import dev.robotcode.robotcode4ij.debugging.RobotEnqueuedArguments
import dev.robotcode.robotcode4ij.debugging.RobotExecutionAttributes
import dev.robotcode.robotcode4ij.debugging.RobotExecutionEventArguments
import org.eclipse.lsp4j.debug.OutputEventArguments
import org.eclipse.lsp4j.debug.OutputEventArgumentsCategory
import org.eclipse.lsp4j.debug.Source
import java.nio.file.Path

class RobotCodeTestEventsConverterTest : BasePlatformTestCase() {

    // the calls the converter makes, one line each
    private inner class RecordingProcessor :
        GeneralTestEventsProcessor(project, "RobotCode", SMTestProxy.SMRootTestProxy()) {
        val calls = mutableListOf<String>()

        override fun onStartTesting() {
            calls.add("startTesting")
        }

        override fun onTestsCountInSuite(count: Int) {
            calls.add("count $count")
        }

        override fun onSuiteStarted(event: TestSuiteStartedEvent) {
            calls.add("suiteStarted ${event.name} ${event.id} ${event.parentId} ${event.locationUrl} ${event.metainfo}")
        }

        override fun onTestStarted(event: TestStartedEvent) {
            calls.add("testStarted ${event.name} ${event.id} ${event.parentId} ${event.locationUrl} ${event.metainfo}")
        }

        override fun onTestFinished(event: TestFinishedEvent) {
            calls.add("testFinished ${event.name} ${event.id} ${event.duration}")
        }

        override fun onTestFailure(event: TestFailedEvent) {
            val trace = event.stacktrace?.let { " trace ${it.replace("\n", " | ")}" } ?: ""
            calls.add(
                "testFailed ${event.name} ${event.id} ${event.localizedFailureMessage} ${event.durationMillis}$trace"
            )
        }

        override fun onTestIgnored(event: TestIgnoredEvent) {
            calls.add("testIgnored ${event.name} ${event.id} ${event.ignoreComment}")
        }

        override fun onSuiteFinished(event: TestSuiteFinishedEvent) {
            calls.add("suiteFinished ${event.name} ${event.id}")
        }

        override fun onTestOutput(event: TestOutputEvent) {
            calls.add("output ${event.id} ${event.outputType} ${event.text}")
        }

        override fun onUncapturedOutput(text: String, outputType: Key<*>) {
            calls.add("uncaptured $outputType $text")
        }

        override fun onError(localizedMessage: String, stackTrace: String?, isCritical: Boolean) {
            calls.add("error $localizedMessage")
        }

        override fun onTestsReporterAttached() {}

        override fun setPrinterProvider(printerProvider: TestProxyPrinterProvider) {}
    }

    private val client = RobotCodeDebugProtocolClient()
    private var awaitedOutput = 0
    private lateinit var converter: RobotOutputToGeneralTestEventsConverter
    private lateinit var processor: RecordingProcessor
    private val source = Path.of(System.getProperty("java.io.tmpdir"), "suite.robot").toString()

    override fun setUp() {
        super.setUp()
        processor = RecordingProcessor()
        converter = RobotOutputToGeneralTestEventsConverter("RobotCode", client) { awaitedOutput++ }
        converter.setProcessor(processor)
    }

    override fun tearDown() {
        try {
            converter.dispose()
        } finally {
            super.tearDown()
        }
    }

    private fun item(
        type: String, id: String, name: String, parentId: String?, line: Int? = null, status: String? = null,
        message: String? = null, elapsed: Int? = null
    ) = RobotExecutionEventArguments(
        type = type, id = id, name = name, parentId = parentId,
        attributes = RobotExecutionAttributes(
            longname = if (parentId == null) name else "Suite.$name", status = status, message = message,
            elapsedtime = elapsed, source = source, lineno = line
        )
    )

    private fun suite(status: String? = null) = item("suite", "s1", "Suite", null, status = status)

    private fun test(
        id: String, name: String, line: Int, status: String? = null, message: String? = null, elapsed: Int? = null
    ) = item("test", id, name, "s1", line, status, message, elapsed)

    private fun url(line: Int) = Urls.newUrl("robotcode", "/", Urls.newLocalFileUrl(source).toString())
        .addParameters(mapOf("line" to line.toString())).toString()

    // the text the console shows for a node when it is selected
    private fun printed(proxy: SMTestProxy): String {
        val out = StringBuilder()
        proxy.printOn(object : Printer {
            override fun print(text: String, contentType: ConsoleViewContentType) {
                out.append(text)
            }

            override fun onNewAvailable(printable: Printable) {
                printable.printOn(this)
            }

            override fun printHyperlink(text: String, info: HyperlinkInfo?) {
                out.append(text)
            }

            override fun mark() {}
        })
        return out.toString()
    }

    fun testEventsOfARunBecomeTheResultsTree() {
        converter.startTesting()
        client.onRobotStarted.fire(suite())
        client.onRobotStarted.fire(test("t1", "First", 5))
        client.onRobotEnded.fire(test("t1", "First", 5, "PASS", elapsed = 12))
        client.onRobotStarted.fire(test("t2", "Second", 8))
        client.onRobotEnded.fire(test("t2", "Second", 8, "FAIL", "intentional failure", 5))
        client.onRobotStarted.fire(test("t3", "Third", 11))
        client.onRobotEnded.fire(test("t3", "Third", 11, "SKIP"))
        client.onRobotEnded.fire(suite("FAIL"))

        assertEquals(
            listOf(
                "startTesting",
                "suiteStarted Suite s1 0 ${url(0)} Suite",
                "testStarted First t1 s1 ${url(4)} Suite.First",
                "testFinished First t1 12",
                "testStarted Second t2 s1 ${url(7)} Suite.Second",
                "testFailed Second t2 intentional failure 5",
                "testStarted Third t3 s1 ${url(10)} Suite.Third",
                "testIgnored Third t3 Skipped",
                "suiteFinished Suite s1",
            ),
            processor.calls
        )
        // every debugger event waits for the process output written before it
        assertEquals(8, awaitedOutput)
    }

    fun testAFailureInAKeywordCarriesTheFailedKeywordsAsItsStackTrace() {
        val resource = Path.of(System.getProperty("java.io.tmpdir"), "common.resource").toString()
        val failed = test("t1", "First", 5, "FAIL", "Hello, Robot != Hello, World", 4).copy(
            failedKeywords = arrayOf(
                RobotExecutionAttributes(kwname = "Build Greeting", libname = "common", source = source, lineno = 6),
                RobotExecutionAttributes(kwname = "Should Be Equal", libname = "BuiltIn", source = resource, lineno = 4)
            )
        )
        converter.startTesting()
        client.onRobotStarted.fire(suite())
        client.onRobotStarted.fire(test("t1", "First", 5))
        client.onRobotEnded.fire(failed)
        client.onRobotStarted.fire(test("t2", "Second", 9))
        client.onRobotEnded.fire(test("t2", "Second", 9, "FAIL", "failed in the test itself", 1))

        assertEquals(
            listOf(
                "testFailed First t1 Hello, Robot != Hello, World 4 trace " +
                    "    at BuiltIn.Should Be Equal ($resource:4) |     at common.Build Greeting ($source:6)",
                "testFailed Second t2 failed in the test itself 1"
            ),
            processor.calls.filter { it.startsWith("testFailed") }
        )
    }

    fun testTheCountOfTheRunReachesTheProgressBeforeTheFirstSuiteStarts() {
        client.onRobotEnqueued.fire(
            RobotEnqueuedArguments(arrayOf("$source;Suite", "$source;Suite.First;5", "$source;Suite.Second;8"))
        )
        client.onRobotStarted.fire(suite())
        converter.startTesting()

        assertEquals(
            listOf("startTesting", "count 2", "suiteStarted Suite s1 0 ${url(0)} Suite"),
            processor.calls
        )
    }

    fun testItemsBeforeTheStartAreAppliedAfterItInTheirOrder() {
        // the command line comes before any debugger event and goes through at once, as before
        converter.process("robotcode debug\n", ProcessOutputTypes.SYSTEM)
        client.onRobotStarted.fire(suite())
        converter.process("Suite\n", ProcessOutputTypes.STDOUT)
        client.onRobotStarted.fire(test("t1", "First", 5))
        assertEquals(listOf("uncaptured system robotcode debug\n"), processor.calls)

        converter.startTesting()

        assertEquals(
            listOf(
                "uncaptured system robotcode debug\n",
                "startTesting",
                "suiteStarted Suite s1 0 ${url(0)} Suite",
                "testStarted First t1 s1 ${url(4)} Suite.First",
            ),
            processor.calls
        )
    }

    fun testItemsAfterTheFinishAreDropped() {
        converter.startTesting()
        converter.finishTesting()

        client.onRobotStarted.fire(suite())
        converter.process("late\n", ProcessOutputTypes.STDOUT)

        assertEquals(listOf("startTesting"), processor.calls)
    }

    fun testSystemTextWithoutALineEndArrivesAtOnce() {
        converter.startTesting()

        converter.process("robotcode debug", ProcessOutputTypes.SYSTEM)

        assertEquals(listOf("startTesting", "uncaptured system robotcode debug"), processor.calls)
    }

    // the process output belongs to the "Terminal" tab; the results tree keeps only the platform's system output
    fun testProcessOutputStaysOutOfTheResultsTree() {
        converter.startTesting()
        client.onRobotStarted.fire(suite())
        converter.process("Suite\n", ProcessOutputTypes.STDOUT)
        client.onRobotStarted.fire(test("t1", "First", 5))
        converter.process("first console\n", ProcessOutputTypes.STDOUT)
        converter.process("[ WARN ] a warning\n", ProcessOutputTypes.STDERR)
        client.onRobotEnded.fire(test("t1", "First", 5, "PASS", elapsed = 1))
        // a status line in the colors that Robot Framework writes when console colors are switched on
        converter.process("| PASS |\n", ProcessOutputType("\u001b[32m", ProcessOutputType.STDOUT))
        converter.process("Process finished\n", ProcessOutputTypes.SYSTEM)

        assertEquals(
            listOf("uncaptured system Process finished\n"),
            processor.calls.filter { it.startsWith("output") || it.startsWith("uncaptured") }
        )
    }

    private fun log(text: String) = OutputEventArguments().apply {
        output = text
        category = OutputEventArgumentsCategory.CONSOLE
    }

    fun testLogMessagesKeepTheirOrderWithNestedSuites() {
        val root = SMTestProxy.SMRootTestProxy()
        converter.setProcessor(GeneralIdBasedToSMTRunnerEventsConvertor(project, root, "RobotCode"))
        converter.startTesting()
        client.onRobotStarted.fire(item("suite", "A", "Tests", null))
        client.onRobotStarted.fire(item("suite", "B", "Inner", "A"))
        client.onOutput.fire(log("suite setup message\n"))
        client.onRobotStarted.fire(item("test", "t1", "First", "B", 5))
        client.onOutput.fire(log("first message\n"))
        client.onRobotEnded.fire(item("test", "t1", "First", "B", 5, "PASS", elapsed = 1))
        client.onRobotStarted.fire(item("test", "t2", "Second", "B", 8))
        client.onOutput.fire(log("second message\n"))
        client.onRobotEnded.fire(item("test", "t2", "Second", "B", 8, "PASS", elapsed = 1))
        client.onRobotEnded.fire(item("suite", "B", "Inner", "A", status = "PASS"))
        client.onRobotEnded.fire(item("suite", "A", "Tests", null, status = "PASS"))
        converter.finishTesting()

        val inner = root.children.single().children.single()
        // the run and a suite show the messages of everything below them in their order, a test only its own
        assertEquals("suite setup message\nfirst message\nsecond message\n", printed(root))
        assertEquals("suite setup message\nfirst message\nsecond message\n", printed(inner))
        assertEquals("first message\n", printed(inner.children[0]))
        assertEquals("second message\n", printed(inner.children[1]))
    }

    fun testDebuggerOutputBelongsToTheInnermostRunningItem() {
        val file = source
        converter.startTesting()
        client.onOutput.fire(OutputEventArguments().apply {
            output = "before"
            category = OutputEventArgumentsCategory.STDOUT
        })
        client.onRobotStarted.fire(suite())
        client.onRobotStarted.fire(test("t1", "First", 5))
        client.onOutput.fire(OutputEventArguments().apply {
            output = "a log message"
            category = OutputEventArgumentsCategory.STDERR
        })
        // a warning of a keyword call and a system message, as the debugger sends them
        client.onOutput.fire(OutputEventArguments().apply {
            output = "[ WARN ] a warning\n"
            category = OutputEventArgumentsCategory.CONSOLE
            source = Source().apply { path = file }
            line = 6
        })
        client.onOutput.fire(OutputEventArguments().apply {
            output = "[ ERROR ] a system message\n"
            category = "messages"
        })

        assertEquals(
            listOf(
                "output 0 stdout before",
                "output t1 stderr a log message",
                "output t1 stdout \u001b[33m[ WARN ] a warning ($file:6)\u001b[0m\n",
                "output t1 stdout \u001b[31m[ ERROR ] a system message\u001b[0m\n",
            ),
            processor.calls.filter { it.startsWith("output") }
        )
    }

    fun testRobotEventsAfterDisposeAreIgnored() {
        converter.startTesting()
        converter.dispose()

        client.onRobotStarted.fire(suite())

        assertEquals(0, awaitedOutput)
        assertEquals(listOf("startTesting"), processor.calls)
    }

    fun testFailedOrSkippedSuiteTeardownMarksTheTestsAgain() {
        converter.startTesting()
        client.onRobotStarted.fire(suite())
        client.onRobotStarted.fire(test("t1", "First", 5))
        client.onRobotEnded.fire(test("t1", "First", 5, "PASS", elapsed = 1))

        client.onRobotSetFailed.fire(test("t1", "First", 5, "FAIL", "Parent suite teardown failed:\nteardown broke"))
        client.onRobotSetFailed.fire(test("t2", "Second", 8, "SKIP", "Skipped in parent suite teardown:\nskipped"))
        client.onRobotSetFailed.fire(test("t3", "Third", 11, "PASS"))

        assertEquals(
            listOf(
                "testFailed First t1 Parent suite teardown failed:\nteardown broke -1",
                "testIgnored Second t2 Skipped in parent suite teardown:\nskipped",
            ),
            processor.calls.drop(4)
        )
    }

    fun testMarkedTestsChangeTheirStateInTheResultsTree() {
        val root = SMTestProxy.SMRootTestProxy()
        converter.setProcessor(GeneralIdBasedToSMTRunnerEventsConvertor(project, root, "RobotCode"))
        converter.startTesting()
        client.onRobotStarted.fire(suite())
        client.onRobotStarted.fire(test("t1", "First", 5))
        client.onRobotEnded.fire(test("t1", "First", 5, "PASS", elapsed = 1))
        client.onRobotStarted.fire(test("t2", "Second", 8))
        client.onRobotEnded.fire(test("t2", "Second", 8, "PASS", elapsed = 1))

        client.onRobotSetFailed.fire(test("t1", "First", 5, "FAIL", "Parent suite teardown failed:\nteardown broke"))
        client.onRobotSetFailed.fire(test("t2", "Second", 8, "SKIP", "Skipped in parent suite teardown:\nskipped"))
        client.onRobotEnded.fire(suite("FAIL"))
        converter.finishTesting()

        val (first, second) = root.children.single().children
        assertEquals(TestStateInfo.Magnitude.FAILED_INDEX, first.magnitudeInfo)
        assertEquals("Parent suite teardown failed:\nteardown broke", first.errorMessage)
        assertEquals(TestStateInfo.Magnitude.IGNORED_INDEX, second.magnitudeInfo)
    }
}
