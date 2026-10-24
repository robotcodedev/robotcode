package dev.robotcode.robotcode4ij.execution

import com.intellij.icons.AllIcons
import com.intellij.ide.ui.LafManagerListener
import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.openapi.actionSystem.ActionToolbar
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonShortcuts
import com.intellij.openapi.actionSystem.DefaultActionGroup
import com.intellij.openapi.actionSystem.Separator
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.ModalityState
import com.intellij.openapi.fileEditor.FileEditor
import com.intellij.openapi.fileEditor.FileEditorPolicy
import com.intellij.openapi.fileEditor.FileEditorProvider
import com.intellij.openapi.fileEditor.FileEditorState
import com.intellij.openapi.fileTypes.FileType
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.DumbAwareAction
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Disposer
import com.intellij.openapi.util.UserDataHolderBase
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.testFramework.LightVirtualFile
import com.intellij.ui.DocumentAdapter
import com.intellij.ui.JBColor
import com.intellij.ui.SearchTextField
import com.intellij.ui.jcef.JBCefBrowser
import dev.robotcode.robotcode4ij.RobotCodeBundle
import org.cef.browser.CefBrowser
import org.cef.handler.CefLifeSpanHandlerAdapter
import org.cef.handler.CefLoadHandlerAdapter
import java.awt.BorderLayout
import java.awt.event.KeyAdapter
import java.awt.event.KeyEvent
import java.beans.PropertyChangeListener
import java.net.URI
import java.net.URISyntaxException
import java.nio.file.Path
import java.util.concurrent.CompletableFuture
import java.util.concurrent.TimeUnit
import javax.swing.Icon
import javax.swing.JComponent
import javax.swing.JPanel
import javax.swing.event.DocumentEvent

/**
 * The file type of the preview tabs: binary, so that nothing takes a tab for a text file (LSP4IJ offers a language
 * server for plain text files whose name ends in `.html`); the tab keeps the icon of a text file.
 */
internal object RobotCodeOutputPreviewFileType : FileType {
    override fun getName(): String = "RobotCode Output Preview"

    override fun getDisplayName(): String = RobotCodeBundle.message("run.preview.fileTypeName")

    override fun getDescription(): String = RobotCodeBundle.message("run.preview.fileType")

    override fun getDefaultExtension(): String = ""

    override fun getIcon(): Icon = AllIcons.FileTypes.Text

    override fun isBinary(): Boolean = true
}

/**
 * The preview tab of the report or log at [path]. Two of them are equal when they show the same file, so that the
 * editor manager finds an open tab again.
 */
internal class RobotCodeOutputPreviewFile(val path: Path) : LightVirtualFile(
    RobotCodeBundle.message("run.preview.fileName", path.fileName.toString()), RobotCodeOutputPreviewFileType, ""
) {

    // the file's own URL, also for a file of the project: the tab reloads itself, and relative links reach the log
    val pageUrl: String
        get() = path.toUri().toString()

    override fun isWritable(): Boolean = false

    override fun equals(other: Any?): Boolean = other is RobotCodeOutputPreviewFile && other.path == path

    override fun hashCode(): Int = path.hashCode()
}

/** The file of a page that the preview shows, without its query and fragment; null for a page that is no file. */
internal fun pagePath(url: String?): Path? {
    return try {
        val uri = URI(url ?: return null)
        if (!"file".equals(uri.scheme, ignoreCase = true) || uri.path == null) return null
        Path.of(URI("file", null, uri.path, null))
    } catch (_: URISyntaxException) {
        null
    } catch (_: IllegalArgumentException) {
        null
    }
}

/**
 * The parameters of the DevTools method `Emulation.setEmulatedMedia` that give the pages of the preview the IDE's light
 * or [dark] theme as `prefers-color-scheme`, which reports and logs of Robot Framework 7.0 and later follow.
 */
internal fun colorSchemeParameters(dark: Boolean): String =
    """{"features":[{"name":"prefers-color-scheme","value":"${if (dark) "dark" else "light"}"}]}"""

/**
 * Shows the report or log of [file] in a browser, below a toolbar to go back and forward, reload, find in the page and
 * open the shown page in the default browser; [reload] loads the file's current content after a run.
 */
internal class RobotCodeOutputPreviewEditor(
    private val project: Project, private val file: RobotCodeOutputPreviewFile
) : UserDataHolderBase(), FileEditor {

    // without the page, which loads once the browser has the IDE's color scheme, so that it shows its theme at once
    private val browser = JBCefBrowser.createBuilder().build()

    // the browser's history, as its last change of the loading state reported it
    @Volatile
    private var canGoBack = false

    @Volatile
    private var canGoForward = false

    private val component = JPanel(BorderLayout())

    private val toolbar: ActionToolbar

    private val findField = SearchTextField(false)

    private val findBar = JPanel(BorderLayout())

    init {
        Disposer.register(this, browser)

        browser.jbCefClient.addLifeSpanHandler(object : CefLifeSpanHandlerAdapter() {
            override fun onAfterCreated(cefBrowser: CefBrowser?) {
                // the page also loads when the color scheme cannot be set, and waits for it at most a second
                applyColorScheme().orTimeout(1, TimeUnit.SECONDS).whenComplete { _, _ -> browser.loadURL(file.pageUrl) }
            }
        }, browser.cefBrowser)
        ApplicationManager.getApplication().messageBus.connect(this)
            .subscribe(LafManagerListener.TOPIC, LafManagerListener { applyColorScheme() })

        val find = action("run.preview.find", AllIcons.Actions.Find) { openFind() }
        toolbar = toolbarOf(
            action("run.preview.back", AllIcons.Actions.Back, { canGoBack }) { runInPage("history.back()") },
            action("run.preview.forward", AllIcons.Actions.Forward, { canGoForward }) {
                runInPage("history.forward()")
            },
            action("run.preview.reload", AllIcons.Actions.Refresh) { browser.cefBrowser.reloadIgnoreCache() },
            Separator.getInstance(),
            find,
            action("run.preview.openInBrowser", AllIcons.General.Web) { openInDefaultBrowser() }
        )
        find.registerCustomShortcutSet(CommonShortcuts.getFind(), component, this)

        browser.jbCefClient.addLoadHandler(object : CefLoadHandlerAdapter() {
            override fun onLoadingStateChange(
                cefBrowser: CefBrowser?, isLoading: Boolean, canGoBack: Boolean, canGoForward: Boolean
            ) {
                this@RobotCodeOutputPreviewEditor.canGoBack = canGoBack
                this@RobotCodeOutputPreviewEditor.canGoForward = canGoForward
                // the browser reports on a thread of its own
                ApplicationManager.getApplication().invokeLater({ toolbar.updateActionsAsync() }, ModalityState.any())
            }
        }, browser.cefBrowser)

        findField.addDocumentListener(object : DocumentAdapter() {
            override fun textChanged(e: DocumentEvent) = find(forward = true, next = false)
        })
        findField.textEditor.addKeyListener(object : KeyAdapter() {
            override fun keyPressed(e: KeyEvent) {
                when (e.keyCode) {
                    KeyEvent.VK_ENTER -> find(forward = !e.isShiftDown, next = true)
                    KeyEvent.VK_ESCAPE -> closeFind()
                    else -> return
                }
                e.consume()
            }
        })
        val findActions = toolbarOf(
            action("run.preview.findPrevious", AllIcons.Actions.PreviousOccurence) {
                find(forward = false, next = true)
            },
            action("run.preview.findNext", AllIcons.Actions.NextOccurence) { find(forward = true, next = true) },
            action("run.preview.findClose", AllIcons.Actions.Close) { closeFind() }
        )
        findBar.add(findField, BorderLayout.CENTER)
        findBar.add(findActions.component, BorderLayout.EAST)
        findBar.isVisible = false

        val top = JPanel(BorderLayout())
        top.add(toolbar.component, BorderLayout.NORTH)
        top.add(findBar, BorderLayout.SOUTH)
        component.add(top, BorderLayout.NORTH)
        component.add(browser.component, BorderLayout.CENTER)
    }

    // the tab's file again: a reload works also after a click changed the fragment, and adds nothing to the history
    fun reload() {
        if (pagePath(browser.cefBrowser.url) == file.path) {
            browser.cefBrowser.reloadIgnoreCache()
        } else {
            browser.loadURL(file.pageUrl)
        }
    }

    // the IDE's light or dark theme as the pages' prefers-color-scheme, for every page of the tab and every later load;
    // without a DevTools client the pages keep the browser's own, and JCEF's client takes no browser of another kind
    private fun applyColorScheme(): CompletableFuture<*> = try {
        browser.cefBrowser.devToolsClient
            ?.executeDevToolsMethod("Emulation.setEmulatedMedia", colorSchemeParameters(dark = !JBColor.isBright()))
            ?: CompletableFuture.completedFuture(null)
    } catch (_: IllegalArgumentException) {
        CompletableFuture.completedFuture(null)
    }

    // the browser's own goBack does nothing in the IDE's JCEF, while the page's history moves
    private fun runInPage(script: String) {
        browser.cefBrowser.executeJavaScript(script, browser.cefBrowser.url, 0)
    }

    private fun toolbarOf(vararg actions: AnAction): ActionToolbar {
        val result = ActionManager.getInstance()
            .createActionToolbar("RobotCodeOutputPreview", DefaultActionGroup(*actions), true)
        result.targetComponent = component
        return result
    }

    private fun action(
        key: String, icon: Icon, enabled: () -> Boolean = { true }, perform: () -> Unit
    ): DumbAwareAction = object : DumbAwareAction(RobotCodeBundle.message(key), null, icon) {
        override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

        override fun update(e: AnActionEvent) {
            e.presentation.isEnabled = enabled()
        }

        override fun actionPerformed(e: AnActionEvent) = perform()
    }

    private fun find(forward: Boolean, next: Boolean) {
        val text = findField.text
        if (text.isEmpty()) {
            browser.cefBrowser.stopFinding(true)
        } else {
            browser.cefBrowser.find(text, forward, false, next)
        }
    }

    private fun openFind() {
        findBar.isVisible = true
        component.revalidate()
        findField.selectText()
        findField.textEditor.requestFocusInWindow()
    }

    private fun closeFind() {
        browser.cefBrowser.stopFinding(true)
        findBar.isVisible = false
        component.revalidate()
        browser.component.requestFocusInWindow()
    }

    private fun openInDefaultBrowser() {
        val path = pagePath(browser.cefBrowser.url) ?: return
        ApplicationManager.getApplication().executeOnPooledThread { openInBrowser(project, path, null) }
    }

    override fun getComponent(): JComponent = component

    override fun getPreferredFocusedComponent(): JComponent = browser.component

    override fun getName(): String = RobotCodeBundle.message("run.preview.editorName")

    override fun getFile(): VirtualFile = file

    override fun setState(state: FileEditorState) = Unit

    override fun isModified(): Boolean = false

    override fun isValid(): Boolean = true

    override fun addPropertyChangeListener(listener: PropertyChangeListener) = Unit

    override fun removePropertyChangeListener(listener: PropertyChangeListener) = Unit

    override fun dispose() = Unit
}

/** Opens the preview tabs of reports and logs, without another editor beside them. */
class RobotCodeOutputPreviewEditorProvider : FileEditorProvider, DumbAware {
    override fun accept(project: Project, file: VirtualFile): Boolean = file is RobotCodeOutputPreviewFile

    override fun acceptRequiresReadAction(): Boolean = false

    override fun createEditor(project: Project, file: VirtualFile): FileEditor =
        RobotCodeOutputPreviewEditor(project, file as RobotCodeOutputPreviewFile)

    override fun getEditorTypeId(): String = "robotcode-output-preview"

    override fun getPolicy(): FileEditorPolicy = FileEditorPolicy.HIDE_OTHER_EDITORS
}
