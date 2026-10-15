package dev.robotcode.robotcode4ij.execution

import com.intellij.icons.AllIcons
import com.intellij.ide.browsers.BrowserLauncher
import com.intellij.ide.browsers.WebBrowser
import com.intellij.ide.browsers.WebBrowserManager
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.ModalityState
import com.intellij.openapi.application.runReadActionBlocking
import com.intellij.openapi.fileEditor.OpenFileDescriptor
import com.intellij.openapi.fileEditor.ex.FileEditorManagerEx
import com.intellij.openapi.project.DumbAwareAction
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.ui.jcef.JBCefApp
import com.intellij.util.Urls
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import dev.robotcode.robotcode4ij.debugging.RobotExitedEventArguments
import org.jetbrains.builtInWebServer.getBuiltInServerUrls
import java.nio.file.Files
import java.nio.file.InvalidPathException
import java.nio.file.Path

/**
 * The report or the log ([kind]) that Robot Framework reported when the run ended ([exited]), when [exists] confirms
 * it; null for [RobotOpenOutput.NONE], before the run reported its files, and for a file that it did not write.
 */
internal fun reportedOutputFile(
    kind: RobotOpenOutput, exited: RobotExitedEventArguments?, exists: (Path) -> Boolean
): Path? {
    val file = when (kind) {
        RobotOpenOutput.NONE -> null
        RobotOpenOutput.REPORT -> exited?.reportFile
        RobotOpenOutput.LOG -> exited?.logFile
    }
    if (file.isNullOrBlank()) return null
    val path = try {
        Path.of(file)
    } catch (_: InvalidPathException) {
        return null
    }
    return path.takeIf(exists)
}

/**
 * Where report and log open for the [target] of the "Run" page: the default browser instead of the built-in preview
 * when the IDE has no JCEF ([previewSupported]), and instead of a browser that is no longer active ([browserActive]).
 */
internal fun effectiveOutputTarget(
    target: RobotOpenOutputTarget, previewSupported: Boolean, browserActive: Boolean
): RobotOpenOutputTarget {
    return when {
        target == RobotOpenOutputTarget.BUILT_IN_PREVIEW && !previewSupported -> RobotOpenOutputTarget.DEFAULT_BROWSER
        target == RobotOpenOutputTarget.BROWSER && !browserActive -> RobotOpenOutputTarget.DEFAULT_BROWSER
        else -> target
    }
}

/** Opens the reported file of [kind] in the target of the "Run" page, when it exists. */
internal fun openReportedOutputFile(project: Project, kind: RobotOpenOutput, exited: RobotExitedEventArguments?) {
    val file = reportedOutputFile(kind, exited) { Files.isRegularFile(it) } ?: return
    // finding the file for a browser refreshes the file system, which may take a while
    ApplicationManager.getApplication().executeOnPooledThread { openOutputFile(project, file) }
}

/** Opens [path] in the target of the "Run" page: in its preview tab, or in a browser. */
private fun openOutputFile(project: Project, path: Path) {
    val settings = RobotCodeProjectConfiguration.getInstance(project)
    val browser = WebBrowserManager.getInstance().activeBrowsers.firstOrNull {
        it.id.toString() == settings.runOpenOutputBrowser
    }
    val target = effectiveOutputTarget(settings.runOpenOutputTarget, JBCefApp.isSupported(), browser != null)
    if (target == RobotOpenOutputTarget.BUILT_IN_PREVIEW) {
        ApplicationManager.getApplication().invokeLater(
            { showPreview(project, path) }, ModalityState.nonModal(), project.disposed
        )
        return
    }
    openInBrowser(project, path, browser.takeIf { target == RobotOpenOutputTarget.BROWSER })
}

/**
 * Opens [path] with the browser launcher, in [browser] or, without one, in the default browser; called off the user
 * interface thread, since finding the file refreshes the file system. The browser gets the file's URL on the IDE's
 * built-in web server, which serves the files of the project, like the "Open In | Browser" menu of HTML files, or its
 * own URL for any other file.
 */
internal fun openInBrowser(project: Project, path: Path, browser: WebBrowser?) {
    val file = LocalFileSystem.getInstance().refreshAndFindFileByNioFile(path) ?: return
    val url = runReadActionBlocking { getBuiltInServerUrls(file, project, null).firstOrNull() }
        ?: Urls.newFromVirtualFile(file)
    ApplicationManager.getApplication().invokeLater(
        { BrowserLauncher.instance.browse(url.toExternalForm(), browser, project) }, ModalityState.nonModal(),
        project.disposed
    )
}

/**
 * Shows [path] in its preview tab: an open tab loads the file again and comes to the front in the editor split where it
 * is; otherwise the tab opens.
 */
private fun showPreview(project: Project, path: Path) {
    val preview = RobotCodeOutputPreviewFile(path)
    val editors = FileEditorManagerEx.getInstanceEx(project)
    val open = editors.getEditorList(preview).filterIsInstance<RobotCodeOutputPreviewEditor>()
    if (open.isEmpty()) {
        OpenFileDescriptor(project, preview).navigate(true)
        return
    }
    open.forEach { it.reload() }
    // navigating would make the tab's split the one in which files open, and take the focus
    editors.windows.filter { it.isFileOpen(preview) }.forEach { it.setSelectedComposite(preview, false) }
}

/**
 * Opens the report or the log of a run in the target of the "Run" page; enabled once the run has reported that it wrote
 * it.
 */
internal class RobotCodeOpenOutputAction(
    private val kind: RobotOpenOutput, private val state: RobotCodeRunProfileState
) : DumbAwareAction() {

    init {
        val key = if (kind == RobotOpenOutput.REPORT) "run.openReport" else "run.openLog"
        templatePresentation.text = RobotCodeBundle.message(key)
        templatePresentation.description = RobotCodeBundle.message("$key.description")
        templatePresentation.icon =
            if (kind == RobotOpenOutput.REPORT) AllIcons.Actions.Report else AllIcons.FileTypes.Html
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = reportedOutputFile(kind, state.robotExited) { Files.isRegularFile(it) } != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        openReportedOutputFile(state.environment.project, kind, state.robotExited)
    }
}
