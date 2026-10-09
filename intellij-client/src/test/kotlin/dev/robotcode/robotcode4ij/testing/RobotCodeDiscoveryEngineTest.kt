package dev.robotcode.robotcode4ij.testing

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.ProcessOutput
import com.intellij.openapi.util.io.FileUtil
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.openapi.vfs.newvfs.events.VFileContentChangeEvent
import com.intellij.openapi.vfs.newvfs.events.VFileDeleteEvent
import com.intellij.openapi.vfs.newvfs.events.VFilePropertyChangeEvent
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import java.io.File
import java.net.URI
import java.util.concurrent.TimeUnit

class RobotCodeDiscoveryEngineTest : BasePlatformTestCase() {

    private val manager get() = project.testManger

    override fun tearDown() {
        try {
            manager.setTestItemsForTests(arrayOf())
            manager.discoverySucceeded()
        } finally {
            super.tearDown()
        }
    }

    private fun change(file: VirtualFile) = VFileContentChangeEvent(null, file, 0, 1)

    private fun suiteFor(file: VirtualFile) =
        RobotCodeTestItem(type = "suite", id = file.path, name = file.name, longname = file.name, uri = file.uri)

    // the test JVM's own java with the sleeper's class folder and the Kotlin standard library, not the whole test class
    // path, which is too long for a command line
    private fun sleeperCommandLine(): GeneralCommandLine {
        val java = ProcessHandle.current().info().command().get()
        val classPath = listOf(DiscoverySleeper::class.java, Unit::class.java).joinToString(File.pathSeparator) { classRoot(it) }
        return GeneralCommandLine(java, "-cp", classPath, DiscoverySleeper::class.java.name)
    }

    // the folder or jar that a class is loaded from
    private fun classRoot(type: Class<*>): String {
        val url = type.getResource(type.simpleName + ".class")!!.toString()
        if (url.startsWith("jar:")) {
            return File(URI(url.removePrefix("jar:").substringBefore("!/"))).path
        }
        return File(URI(url)).path.removeSuffix(type.name.replace('.', File.separatorChar) + ".class")
    }

    fun testCancellingADiscoveryEndsItsProcess() {
        runBlocking {
            var process: Process? = null
            var output: ProcessOutput? = null
            val job = launch(Dispatchers.IO) {
                output = runDiscoveryProcess(sleeperCommandLine(), "") { process = it }
            }
            val deadline = System.currentTimeMillis() + 30_000
            while (process == null && System.currentTimeMillis() < deadline) {
                Thread.sleep(50)
            }
            Thread.sleep(1000)
            assertTrue("the process ended by itself: ${output?.stdout} ${output?.stderr}", process!!.isAlive)

            job.cancelAndJoin()

            assertTrue(process!!.waitFor(10, TimeUnit.SECONDS))
        }
    }

    fun testAProcessThatEndsWithoutReadingItsInputGivesItsExitCode() {
        // more input than a pipe holds, so that writing it fails once the process has ended
        val stdin = "x".repeat(4 * 1024 * 1024)

        val output = runBlocking { runDiscoveryProcess(sleeperCommandLine().withParameters("3"), stdin) }

        assertEquals(3, output.exitCode)
    }

    fun testCancelledDiscoveryKeepsTheModel() {
        val items = arrayOf(RobotCodeTestItem(type = "suite", id = "s", name = "S", longname = "S"))
        manager.setTestItemsForTests(items)

        runBlocking {
            val job = launch(Dispatchers.IO) { manager.runFullDiscovery(sleeperCommandLine()) }
            Thread.sleep(2000)
            job.cancelAndJoin()
        }

        assertSame(items, manager.testItems)
        assertNull(manager.failureNotification)
    }

    fun testFileEventsMapToTheirDiscoveries() {
        val known = myFixture.addFileToProject("known.robot", "*** Test Cases ***\nA\n    Log    a\n").virtualFile
        val unknown = myFixture.addFileToProject("unknown.robot", "*** Test Cases ***\nB\n    Log    b\n").virtualFile
        val notes = myFixture.addFileToProject("notes.txt", "").virtualFile
        val folder = myFixture.addFileToProject("folder/inner.robot", "").virtualFile.parent
        manager.setTestItemsForTests(arrayOf(suiteFor(known)))

        assertEquals(DiscoveryWork(false, setOf(known.uri)), manager.discoveryWork(listOf(change(known))))
        assertEquals(DiscoveryWork(true, emptySet()), manager.discoveryWork(listOf(change(unknown))))
        assertEquals(DiscoveryWork(true, emptySet()), manager.discoveryWork(listOf(VFileDeleteEvent(null, known))))
        assertEquals(DiscoveryWork(true, emptySet()), manager.discoveryWork(listOf(VFileDeleteEvent(null, folder))))
        assertEquals(
            DiscoveryWork(true, emptySet()),
            manager.discoveryWork(
                listOf(VFilePropertyChangeEvent(null, notes, VirtualFile.PROP_NAME, "notes.txt", "renamed.robot"))
            )
        )

        // nothing for other files, other properties and other projects
        assertTrue(manager.discoveryWork(listOf(change(notes))).isEmpty)
        assertTrue(
            manager.discoveryWork(
                listOf(VFilePropertyChangeEvent(null, known, VirtualFile.PROP_WRITABLE, true, false))
            ).isEmpty
        )
        val other = File(FileUtil.createTempDirectory("other-project", null), "suite.robot").apply { writeText("") }
        val otherFile = LocalFileSystem.getInstance().refreshAndFindFileByIoFile(other)!!
        assertTrue(manager.discoveryWork(listOf(change(otherFile), VFileDeleteEvent(null, otherFile))).isEmpty)
    }

    fun testOneNotificationPerFailure() {
        manager.reportFailure("Error: Invalid TOML file")
        val first = manager.failureNotification!!
        assertFalse(first.isExpired)

        // the same failure shows nothing new
        manager.reportFailure("Error: Invalid TOML file")
        assertSame(first, manager.failureNotification)

        // another failure replaces it
        manager.reportFailure("Error: something else")
        val second = manager.failureNotification!!
        assertTrue(first.isExpired)
        assertNotSame(first, second)

        // a successful discovery removes it
        manager.discoverySucceeded()
        assertTrue(second.isExpired)
        assertNull(manager.failureNotification)
    }
}
