package dev.robotcode.robotcode4ij.testing

import com.intellij.codeInsight.daemon.DaemonCodeAnalyzer
import com.intellij.execution.CantRunException
import com.intellij.execution.ExecutionException
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.CapturingProcessAdapter
import com.intellij.execution.process.OSProcessHandler
import com.intellij.execution.process.ProcessOutput
import com.intellij.notification.Notification
import com.intellij.notification.NotificationAction
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.Disposable
import com.intellij.openapi.application.readAction
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.editor.EditorFactory
import com.intellij.openapi.editor.event.DocumentEvent
import com.intellij.openapi.editor.event.DocumentListener
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.fileTypes.FileTypeManager
import com.intellij.openapi.fileTypes.FileTypeRegistry
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.ProjectLocator
import com.intellij.openapi.roots.ProjectFileIndex
import com.intellij.openapi.util.text.StringUtil
import com.intellij.openapi.vfs.AsyncFileListener
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.openapi.vfs.VirtualFileManager
import com.intellij.openapi.vfs.newvfs.events.VFileContentChangeEvent
import com.intellij.openapi.vfs.newvfs.events.VFileCopyEvent
import com.intellij.openapi.vfs.newvfs.events.VFileCreateEvent
import com.intellij.openapi.vfs.newvfs.events.VFileEvent
import com.intellij.openapi.vfs.newvfs.events.VFilePropertyChangeEvent
import com.intellij.platform.ide.progress.withBackgroundProgress
import com.intellij.psi.PsiDirectory
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.util.elementType
import com.intellij.psi.util.startOffset
import com.intellij.util.PathUtil
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.PythonInterpreter
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotCodeEnvironmentListener
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import dev.robotcode.robotcode4ij.isRobotCodeDisabled
import dev.robotcode.robotcode4ij.listeners.ownsEvent
import dev.robotcode.robotcode4ij.psi.IRobotFrameworkElementType
import dev.robotcode.robotcode4ij.psi.RobotSuiteFile
import dev.robotcode.robotcode4ij.recordDiscoverySnapshot
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import org.jetbrains.annotations.TestOnly
import org.jetbrains.annotations.VisibleForTesting
import java.io.IOException
import java.net.URI
import java.nio.file.Paths
import java.util.concurrent.ConcurrentHashMap

private const val POLL_MILLIS = 100L

/**
 * Runs a discovery process with [stdin] as its input and returns its output. A cancelled coroutine ends the process.
 * [started] gets the process as soon as it runs.
 */
internal suspend fun runDiscoveryProcess(
    commandLine: GeneralCommandLine,
    stdin: String,
    started: (Process) -> Unit = {}
): ProcessOutput {
    val output = ProcessOutput()
    val handler = OSProcessHandler(commandLine)
    started(handler.process)
    handler.addProcessListener(CapturingProcessAdapter(output))
    try {
        handler.processInput.bufferedWriter(Charsets.UTF_8).use { it.write(stdin) }
    } catch (_: IOException) {
        // a process that ends before it reads its input reports the reason through its exit code and output
    }
    handler.startNotify()
    try {
        while (!handler.waitFor(POLL_MILLIS)) {
            currentCoroutineContext().ensureActive()
        }
    } finally {
        if (!handler.isProcessTerminated) {
            handler.destroyProcess()
        }
    }
    return output
}

/** The discoveries that a set of file events needs: a full one, or the discoveries of single files by URI. */
internal data class DiscoveryWork(val full: Boolean, val files: Set<String>) {
    val isEmpty: Boolean
        get() = !full && files.isEmpty()
}

// URIs of the same file can differ in their spelling; the path decides
private fun uriPath(uri: String): String = try {
    URI.create(uri).path ?: uri
} catch (_: IllegalArgumentException) {
    uri
}

/**
 * The discovered tests of the project. Discoveries run one at a time on the service's scope, and the model is an
 * immutable tree that only a successful discovery replaces, so run markers and context runs always see one complete
 * result.
 */
@Service(Service.Level.PROJECT)
class RobotCodeTestManager(private val project: Project, private val scope: CoroutineScope) : Disposable,
                                                                                              DocumentListener,
                                                                                              AsyncFileListener {
    companion object {
        private const val DEBOUNCE_DELAY = 1000L
        private const val ERROR_LINES = 5
        private const val NOTIFICATION_GROUP = "RobotCode"
    }
    
    // one discovery at a time
    @OptIn(ExperimentalCoroutinesApi::class)
    private val discoveryDispatcher = Dispatchers.IO.limitedParallelism(1)
    
    // the pending and running discoveries of single files, by URI
    private val fileJobs = ConcurrentHashMap<String, Job>()
    
    @Volatile
    private var fullJob: Job? = null
    
    @Volatile
    var testItems: Array<RobotCodeTestItem> = arrayOf()
        private set
    
    // Whether the project's Robot Framework version supports `--parseinclude` (RF >= 6.1).
    // A per-project environment fact, taken from the last full discover.
    @Volatile
    var supportsParseInclude: Boolean = false
        private set
    
    // the problems that discovery reports, by the path of the file's URI
    @Volatile
    private var diagnostics: Map<String, List<DiscoverDiagnostic>> = emptyMap()
    
    @Volatile
    @VisibleForTesting
    internal var failureNotification: Notification? = null
        private set
    
    @Volatile
    private var failureText: String? = null
    
    init {
        EditorFactory.getInstance().eventMulticaster.addDocumentListener(this, this)
        VirtualFileManager.getInstance().addAsyncFileListener(this, this)
    }
    
    override fun dispose() {
    }
    
    override fun documentChanged(event: DocumentEvent) {
        val file = FileDocumentManager.getInstance().getFile(event.document) ?: return
        if (file.fileType != RobotSuiteFileType || project !in ProjectLocator.getInstance().getProjectsForFile(file)) {
            return
        }
        if (findTestItem(file.uri) != null) {
            requestFile(file.uri)
        } else {
            refreshDebounced()
        }
    }
    
    override fun prepareChange(events: List<VFileEvent>): AsyncFileListener.ChangeApplier? {
        val work = discoveryWork(events)
        if (work.isEmpty) {
            return null
        }
        return object : AsyncFileListener.ChangeApplier {
            override fun afterVfsChange() {
                if (work.full) {
                    refreshDebounced()
                } else {
                    work.files.forEach { requestFile(it) }
                }
            }
        }
    }
    
    /**
     * The discoveries that [events] need, decided before the change, while deleted files still exist. A content change
     * of a known suite file needs the discovery of that file; creating, deleting, moving or renaming suite files or
     * folders of the project needs a full discovery. Events of other projects need nothing.
     */
    internal fun discoveryWork(events: List<VFileEvent>): DiscoveryWork {
        var full = false
        val files = linkedSetOf<String>()
        for (event in events) {
            if (event is VFilePropertyChangeEvent && event.propertyName != VirtualFile.PROP_NAME) {
                continue
            }
            if (!(isSuiteEvent(event) || isFolderEvent(event)) || !project.ownsEvent(event)) {
                continue
            }
            val file = event.file
            if (event is VFileContentChangeEvent && file != null && findTestItem(file.uri) != null) {
                files.add(file.uri)
            } else {
                full = true
            }
        }
        return DiscoveryWork(full, if (full) emptySet() else files)
    }
    
    private fun isSuiteEvent(event: VFileEvent): Boolean {
        val names = listOfNotNull(
            PathUtil.getFileName(event.path),
            (event as? VFilePropertyChangeEvent)?.newValue as? String,
            (event as? VFileCopyEvent)?.newChildName
        )
        return names.any { FileTypeRegistry.getInstance().getFileTypeByFileName(it) == RobotSuiteFileType }
    }
    
    // folders that the project excludes or the IDE ignores, such as `.git` or `__pycache__`, do not count
    private fun isFolderEvent(event: VFileEvent): Boolean {
        val index = ProjectFileIndex.getInstance(project)
        if (event is VFileCreateEvent) {
            return event.isDirectory && !FileTypeManager.getInstance().isFileIgnored(event.childName) &&
                !index.isExcluded(event.parent)
        }
        val file = event.file ?: return false
        return file.isDirectory && !index.isExcluded(file)
    }
    
    fun refreshDebounced(file: VirtualFile) {
        requestFile(file.uri)
    }
    
    @Synchronized
    private fun requestFile(uri: String) {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        fileJobs.remove(uri)?.cancel()
        val job = scope.launch(discoveryDispatcher, start = CoroutineStart.LAZY) {
            try {
                delay(DEBOUNCE_DELAY)
                discoverFile(uri)
            } finally {
                fileJobs.remove(uri, coroutineContext[Job])
            }
        }
        fileJobs[uri] = job
        job.start()
    }
    
    /**
     * Requests a full discovery after a short delay. It cancels a running discovery and the pending discoveries of
     * single files.
     */
    @Synchronized
    fun refreshDebounced() {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        fileJobs.values.forEach { it.cancel() }
        fullJob?.cancel()
        fullJob = scope.launch(discoveryDispatcher) {
            delay(DEBOUNCE_DELAY)
            discoverAll()
        }
    }
    
    // a usable result of the environment check and switching RobotCode on run discovery again
    private fun canDiscover(): Boolean {
        return project.isOpen && !project.isDisposed && project.robotCodeEnvironment.projectState.isUsable &&
            !project.isRobotCodeDisabled
    }
    
    private suspend fun discoverAll() {
        if (!canDiscover()) {
            return
        }
        val commandLine = try {
            project.fullDiscoveryCommandLine()
        } catch (_: CantRunException) {
            return
        }
        project.recordDiscoverySnapshot(commandLine)
        withBackgroundProgress(project, RobotCodeBundle.message("discovery.progress")) {
            runFullDiscovery(commandLine)
        }
    }
    
    /**
     * Runs a full discovery with [commandLine] and replaces the model with its result. A failed or cancelled discovery
     * leaves the model as it is.
     */
    internal suspend fun runFullDiscovery(commandLine: GeneralCommandLine) {
        thisLogger().info("Discovering the tests of the project")
        val result = discover(commandLine, openFiles(null)) ?: return
        testItems = result.items ?: arrayOf()
        supportsParseInclude = result.supportsParseInclude ?: false
        diagnostics = result.diagnostics.orEmpty().mapKeys { uriPath(it.key) }
        DaemonCodeAnalyzer.getInstance(project).restart("RobotCode test items refreshed")
    }
    
    private suspend fun discoverFile(uri: String) {
        if (!canDiscover()) {
            return
        }
        val suite = findTestItem(uri) ?: return
        val commandLine = try {
            project.buildRobotCodeCommandLine(
                fileDiscoveryArguments(suite.longname, suite.relSource, supportsParseInclude), format = "json"
            ).withCharset(Charsets.UTF_8).withWorkDirectory(project.basePath)
        } catch (_: CantRunException) {
            return
        }
        thisLogger().info("Discovering the tests of $uri")
        val result = discover(commandLine, openFiles(uri)) ?: return
        
        // a file that no longer yields its suite with tests or tasks is left to a full discovery, as in VS Code
        val updated = findSuiteChildren(result.items, suite.id)?.let { replaceSuiteChildren(testItems, suite.id, it) }
        if (updated == null) {
            refreshDebounced()
            return
        }
        testItems = updated
        val path = uriPath(uri)
        val problems = result.diagnostics.orEmpty().entries.firstOrNull { uriPath(it.key) == path }?.value
        diagnostics = if (problems.isNullOrEmpty()) diagnostics - path else diagnostics + (path to problems)
        DaemonCodeAnalyzer.getInstance(project).restart("RobotCode test items refreshed for $uri")
    }
    
    // the text of the open editors, all of them or the one of [uri]
    private suspend fun openFiles(uri: String?): String {
        val texts = readAction {
            FileEditorManager.getInstance(project).openFiles.filter { uri == null || it.uri == uri }.mapNotNull { file ->
                FileDocumentManager.getInstance().getDocument(file)?.let { file.uri to it.text }
            }.toMap()
        }
        return Json.encodeToString(texts)
    }
    
    /**
     * Runs a discovery process and decodes its output. A failure is logged and reported, and gives null.
     */
    private suspend fun discover(commandLine: GeneralCommandLine, stdin: String): RobotCodeDiscoverResult? {
        val output = try {
            runDiscoveryProcess(commandLine, stdin)
        } catch (e: ExecutionException) {
            discoveryFailed(commandLine, null, RobotCodeBundle.message("discovery.failed.notStarted", e.message ?: ""))
            return null
        }
        if (output.exitCode != 0) {
            val lines = output.stderr.lines().filter { it.isNotBlank() }.take(ERROR_LINES).joinToString("\n")
            discoveryFailed(
                commandLine, output,
                lines.ifEmpty { RobotCodeBundle.message("discovery.failed.exitCode", output.exitCode.toString()) }
            )
            return null
        }
        val result = try {
            decodeDiscoverResult(output.stdout)
        } catch (e: IllegalArgumentException) {
            discoveryFailed(commandLine, output, RobotCodeBundle.message("discovery.failed.output", e.message ?: ""))
            return null
        }
        discoverySucceeded()
        return result
    }
    
    private fun discoveryFailed(commandLine: GeneralCommandLine, output: ProcessOutput?, text: String) {
        thisLogger().warn(
            "Discovery failed: ${commandLine.commandLineString}\n" +
                (output?.let { "exit code: ${it.exitCode}\nstdout: ${it.stdout}\nstderr: ${it.stderr}" } ?: text)
        )
        reportFailure(text)
    }
    
    /**
     * Shows one notification for a failure: the same failure again shows nothing new, another one replaces it.
     */
    @VisibleForTesting
    internal fun reportFailure(text: String) {
        if (text == failureText && failureNotification?.isExpired == false) {
            return
        }
        failureNotification?.expire()
        failureText = text
        val content = text.lines().joinToString("<br>") { StringUtil.escapeXmlEntities(it) }
        val notification = NotificationGroupManager.getInstance().getNotificationGroup(NOTIFICATION_GROUP)
            .createNotification(RobotCodeBundle.message("discovery.failed.title"), content, NotificationType.ERROR)
        notification.addAction(NotificationAction.createSimpleExpiring(RobotCodeBundle.message("discovery.retry")) {
            refreshDebounced()
        })
        robotToml()?.let { file ->
            notification.addAction(NotificationAction.createSimple(RobotCodeBundle.message("discovery.openRobotToml")) {
                FileEditorManager.getInstance(project).openFile(file, true)
            })
        }
        failureNotification = notification
        notification.notify(project)
    }
    
    /** A successful discovery removes the notification of the last failure. */
    @VisibleForTesting
    internal fun discoverySucceeded() {
        failureNotification?.expire()
        failureNotification = null
        failureText = null
    }
    
    private fun robotToml(): VirtualFile? {
        val base = project.basePath ?: return null
        return LocalFileSystem.getInstance().findFileByNioFile(Paths.get(base, "robot.toml"))
    }
    
    /**
     * The messages of the problems that discovery reported for the file of [uri].
     */
    fun problems(uri: String): List<String> {
        return diagnostics[uriPath(uri)]?.map { it.message }.orEmpty()
    }
    
    /**
     * Forgets the result of the last discovery, so that its run markers disappear.
     */
    fun clearTestItems() {
        testItems = arrayOf()
        diagnostics = emptyMap()
        DaemonCodeAnalyzer.getInstance(project).restart("RobotCode test items cleared")
    }
    
    @TestOnly
    internal fun setTestItemsForTests(items: Array<RobotCodeTestItem>) {
        testItems = items
    }
    
    @TestOnly
    internal fun setDiagnosticsForTests(problems: Map<String, List<DiscoverDiagnostic>>) {
        diagnostics = problems.mapKeys { uriPath(it.key) }
    }
    
        fun findTestItem(
        uri: String,
        line: UInt? = null,
    ): RobotCodeTestItem? {
        return findTestItem(testItems, uri, line)
    }
    
    fun findTestItem(
        root: RobotCodeTestItem,
        uri: String,
        line: UInt? = null,
    ): RobotCodeTestItem? {
        
        if (line == null) {
            if (root.isSameUri(uri)) {
                return root
            }
        } else {
            if (root.isSameUri(uri) && root.range != null && root.range.start.line == line) {
                return root
            }
        }
        
        return findTestItem(root.children ?: arrayOf(), uri, line)
    }
    
    fun findTestItem(
        testItems: Array<RobotCodeTestItem>, uri: String, line: UInt? = null
    ): RobotCodeTestItem? {
        testItems.forEach { item ->
            val found = findTestItem(item, uri, line)
            if (found != null) {
                return found
            }
        }
        
        return null
    }
    
    
    fun findTestItem(element: PsiElement): RobotCodeTestItem? {
        val directory = element as? PsiDirectory
        if (directory != null) {
            return findTestItem(directory.virtualFile.uri)
        }
        
        val containingFile = element.containingFile ?: return null
        if (containingFile !is RobotSuiteFile) {
            return null
        }
        
        if (element is RobotSuiteFile) {
            return findTestItem(containingFile.virtualFile.uri)
        }
        
        if (element.elementType !is IRobotFrameworkElementType) {
            return null
        }
        
        val psiDocumentManager = PsiDocumentManager.getInstance(project) ?: return null
        val document = psiDocumentManager.getDocument(containingFile) ?: return null
        val lineNumber = document.getLineNumber(element.startOffset)
        if (lineNumber <= 0) return null // this is a suite file and this is already caught above
        
        val columnNumber = element.startOffset - document.getLineStartOffset(lineNumber)
        if (columnNumber != 0) return null
        
        val result = findTestItem(containingFile.virtualFile.uri, lineNumber.toUInt())
        return result
    }
}

/**
 * Removes the run markers while the project's interpreter is not usable, because no test can run then. A usable result
 * starts a discovery, which brings them back.
 */
class RobotCodeTestManagerEnvironmentListener(private val project: Project) : RobotCodeEnvironmentListener {
    override fun stateChanged(interpreter: PythonInterpreter, state: EnvironmentState) {
        val notUsable = state is EnvironmentState.Failed || (state is EnvironmentState.Checked && !state.isUsable)
        if (notUsable && interpreter == project.robotCodeEnvironment.projectInterpreter) {
            project.testManger.clearTestItems()
        }
    }
}

private fun getRfcCompliantUri(virtualFile: VirtualFile): String {
    val filePath = virtualFile.path
    
    val normalizedPath = if (isWindows()) {
        filePath.replace("\\", "/")
    } else {
        filePath
    }
    
    return Paths.get(normalizedPath).toUri().toString().removeSuffix("/")
}

private fun isWindows(): Boolean = System.getProperty("os.name").lowercase().contains("win")

val VirtualFile.uri: String
    get() {
        return getRfcCompliantUri(this)
    }

val Project.testManger: RobotCodeTestManager
    get() {
        return this.service<RobotCodeTestManager>()
    }
