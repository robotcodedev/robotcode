package dev.robotcode.robotcode4ij.testing

import com.intellij.codeInsight.daemon.DaemonCodeAnalyzer
import com.intellij.execution.process.CapturingProcessHandler
import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.editor.EditorFactory
import com.intellij.openapi.editor.event.DocumentEvent
import com.intellij.openapi.editor.event.DocumentListener
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.fileEditor.FileEditorManagerListener
import com.intellij.openapi.fileEditor.ex.FileEditorManagerEx
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.ProjectLocator
import com.intellij.openapi.vfs.AsyncFileListener
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.openapi.vfs.VirtualFileManager
import com.intellij.openapi.vfs.newvfs.events.VFileEvent
import com.intellij.psi.PsiDirectory
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.util.elementType
import com.intellij.psi.util.startOffset
import com.intellij.util.io.URLUtil
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import dev.robotcode.robotcode4ij.psi.IRobotFrameworkElementType
import dev.robotcode.robotcode4ij.psi.RobotSuiteFile
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.net.URI
import java.util.*


@Service(Service.Level.PROJECT) class RobotCodeTestManager(private val project: Project) : Disposable, DocumentListener,
                                                                                           AsyncFileListener,
                                                                                           FileEditorManagerListener {
    companion object {
        private const val DEBOUNCE_DELAY = 1000L
    }
    
    private val refreshJobs = WeakHashMap<VirtualFile, Job>()
    private var refreshJob: Job? = null
    
    var testItems: Array<RobotCodeTestItem> = arrayOf()
        private set
    
    init {
        EditorFactory.getInstance().eventMulticaster.addDocumentListener(this, this)
        VirtualFileManager.getInstance().addAsyncFileListener(this, this)
        project.messageBus.connect().subscribe(FileEditorManagerListener.FILE_EDITOR_MANAGER, this)
    }
    
    override fun dispose() {
        EditorFactory.getInstance().eventMulticaster.removeDocumentListener(this)
    }
    
    override fun documentChanged(event: DocumentEvent) {
        super.documentChanged(event)
        FileDocumentManager.getInstance().getFile(event.document)?.let { file ->
            ProjectLocator.getInstance().getProjectsForFile(file).let { projects ->
                if (project in projects) {
                    if (file.fileType == RobotSuiteFileType) {
                        if (findTestItem(file.uri) != null) {
                            refreshDebounced(file)
                        } else {
                            refreshDebounced()
                        }
                    }
                }
                
            }
        }
    }
    
    override fun prepareChange(events: List<VFileEvent>): AsyncFileListener.ChangeApplier? {
        return object : AsyncFileListener.ChangeApplier {
            override fun afterVfsChange() {
                events.forEach { event ->
                    val file = event.file
                    if (file != null) {
                        if (file.fileType == RobotSuiteFileType) {
                            if (findTestItem(file.uri) != null) {
                                refreshDebounced(file)
                            } else {
                                refreshDebounced()
                            }
                            
                        }
                    }
                }
            }
        }
    }
    
    override fun fileOpened(source: FileEditorManager, file: VirtualFile) {
        if (file.fileType == RobotSuiteFileType) {
            refreshDebounced(file)
        }
    }
    
    override fun fileClosed(source: FileEditorManager, file: VirtualFile) {
        if (file.fileType == RobotSuiteFileType) {
            refreshDebounced(file)
        }
    }
    
    private val refreshScope = CoroutineScope(Dispatchers.Default)
    
    fun refreshDebounced(file: VirtualFile) {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        
        val job = refreshJobs[file]
        
        if (job != null) {
            thisLogger().info("Cancelling previous refresh job")
            job.cancel()
        }
        if (refreshJob != null) {
            thisLogger().info("Cancelling previous refresh job")
            runBlocking { refreshJob?.join() }
        }
        refreshJobs[file] = refreshScope.launch {
            delay(DEBOUNCE_DELAY)
            refresh(file.uri)
            refreshJobs.remove(file)
        }
    }
    
    fun refreshDebounced() {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        
        refreshJobs.values.forEach { it.cancel() }
        refreshJob?.cancel()
        
        refreshJob = refreshScope.launch {
            delay(DEBOUNCE_DELAY)
            refresh()
            refreshJob = null
        }
    }
    
    fun refresh(uri: String) {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        
        thisLogger().info("Refreshing test items for $uri")
        try {
            val testItem = findTestItem(uri) ?: return
            
            testItem.children = ApplicationManager.getApplication().executeOnPooledThread<RobotCodeDiscoverResult> {
                
                // TODO: Add support for configurable paths
                val defaultPaths = arrayOf("--default-path", ".")
                
                val cmdLine = project.buildRobotCodeCommandLine(
                    arrayOf(
                        *defaultPaths,
                        "discover",
                        "--read-from-stdin",
                        "tests",
                        *(if (testItem.needsParseInclude == true && testItem.relSource != null) arrayOf(
                            "--needs-parse-include", testItem.relSource
                        )
                        else arrayOf<String>()),
                        "--suite",
                        testItem.longname
                    ), format = "json"
                ).withCharset(Charsets.UTF_8).withWorkDirectory(project.basePath)
                
                var openFiles = mutableMapOf<String, String>()
                
                ApplicationManager.getApplication().runReadAction {
                    FileEditorManagerEx.getInstanceEx(project).openFiles.forEach { file ->
                        if (file.uri == uri) {
                            FileDocumentManager.getInstance().getDocument(file)?.let { document ->
                                openFiles[file.uri] = document.text
                            }
                        }
                    }
                }
                
                var openFilesAsString = Json.encodeToString(openFiles)
                
                val result = CapturingProcessHandler(cmdLine).apply {
                    process.outputStream.bufferedWriter().apply {
                        write(openFilesAsString)
                        flush()
                        close()
                    }
                }.runProcess()
                
                if (result.exitCode != 0) {
                    throw RuntimeException("Failed to discover test items for $uri: ${result.stderr}")
                }
                Json.decodeFromString<RobotCodeDiscoverResult>(result.stdout)
            }.get()?.items ?: arrayOf()
        } catch (e: Exception) {
            thisLogger().warn("Failed to discover test items", e)
        }
        
        DaemonCodeAnalyzer.getInstance(project).restart()
    }
    
    fun refresh() {
        thisLogger().info("Refreshing test items")
        try {
            testItems = ApplicationManager.getApplication().executeOnPooledThread<RobotCodeDiscoverResult> {
                
                // TODO: Add support for configurable paths
                val defaultPaths = arrayOf("--default-path", ".")
                
                val cmdLine = project.buildRobotCodeCommandLine(
                    arrayOf(*defaultPaths, "discover", "--read-from-stdin", "all"), format = "json"
                ).withCharset(Charsets.UTF_8).withWorkDirectory(project.basePath)
                
                var openFiles = mutableMapOf<String, String>()
                
                ApplicationManager.getApplication().runReadAction {
                    FileEditorManagerEx.getInstanceEx(project).openFiles.forEach { file ->
                        FileDocumentManager.getInstance().getDocument(file)?.let { document ->
                            openFiles[file.uri] = document.text
                        }
                    }
                }
                
                var openFilesAsString = Json.encodeToString(openFiles)
                
                val result = CapturingProcessHandler(cmdLine).apply {
                    process.outputStream.bufferedWriter().apply {
                        write(openFilesAsString)
                        flush()
                        close()
                    }
                }.runProcess()
                
                if (result.exitCode != 0) {
                    throw RuntimeException("Failed to discover test items: ${result.stderr}")
                }
                Json.decodeFromString<RobotCodeDiscoverResult>(result.stdout)
            }.get()?.items ?: arrayOf()
        } catch (e: Exception) {
            thisLogger().warn("Failed to discover test items", e)
            testItems = arrayOf()
        }
        
        DaemonCodeAnalyzer.getInstance(project).restart()
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
            if (root.uri == uri) {
                return root
            }
        } else {
            if (root.uri == uri && root.range != null && root.range.start.line == line) {
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

val VirtualFile.uri: String
    get() {
        return URI.create(fileSystem.protocol + URLUtil.SCHEME_SEPARATOR + "/" + path.replace(":", "%3A")).toString()
    }

val Project.testManger: RobotCodeTestManager
    get() {
        return this.service<RobotCodeTestManager>()
    }
