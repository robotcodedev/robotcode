package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.ServerStatus
import com.redhat.devtools.lsp4ij.client.IndexAwareLanguageClient
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettingsMapper
import dev.robotcode.robotcode4ij.configuration.profileListCache
import dev.robotcode.robotcode4ij.configuration.selectionCheck
import org.eclipse.lsp4j.MessageParams

private val MARKDOWN_PUNCTUATION = Regex("""[!-/:-@\[-`{-~]""")

/** [text] with every ASCII punctuation character escaped with a backslash, which Markdown shows as the character. */
internal fun escapeMarkdown(text: String): String = MARKDOWN_PUNCTUATION.replace(text) { "\\" + it.value }

class RobotCodeLanguageClient(project: Project) : IndexAwareLanguageClient(project) {

    // LSP4IJ shows a message as Markdown, but the server sends plain text, such as a pattern like `*base*` or the
    // `<unknown>` of a Python error
    override fun showMessage(messageParams: MessageParams) {
        super.showMessage(MessageParams(messageParams.type, escapeMarkdown(messageParams.message)))
    }

    override fun handleServerStatusChanged(serverStatus: ServerStatus) {
        when (serverStatus) {
            ServerStatus.started -> {
                triggerChangeConfiguration()
                project.robotCodeProjectInfo.serverStarted()
                // the server also starts again after a change to robot.toml, which may change the profiles; the run
                // configurations' warning about profiles that no longer exist needs the list without a dialog open
                project.profileListCache.reload()
                // a selection that names a profile that robot.toml does not define is reported with its fixes
                project.selectionCheck.check()
            }

            ServerStatus.stopping, ServerStatus.stopped -> project.robotCodeProjectInfo.serverStopped()
            else -> {}
        }
    }
    
    override fun createSettings(): Any {
        return RobotCodeServerSettingsMapper.toJsonTree(project)
    }
}
