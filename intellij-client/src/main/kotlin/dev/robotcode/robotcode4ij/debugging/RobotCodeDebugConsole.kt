package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.console.BaseConsoleExecuteActionHandler
import com.intellij.execution.console.ConsoleExecuteAction
import com.intellij.execution.console.ConsoleHistoryController
import com.intellij.execution.console.ConsoleRootType
import com.intellij.execution.console.LanguageConsoleImpl
import com.intellij.execution.console.LanguageConsoleView
import com.intellij.execution.ui.ConsoleViewContentType
import com.intellij.ide.scratch.RootType
import com.intellij.openapi.Disposable
import com.intellij.openapi.util.Disposer
import com.intellij.xdebugger.XDebugSession
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import org.eclipse.lsp4j.debug.EvaluateArguments
import org.eclipse.lsp4j.debug.EvaluateArgumentsContext
import org.eclipse.lsp4j.jsonrpc.ResponseErrorException
import java.util.concurrent.CompletionException

/** The root of the Robot Debug Console's history among the scratch files. */
class RobotCodeDebugConsoleRootType :
    ConsoleRootType("robotcode-debug-console", RobotCodeBundle.message("debugger.console.title"))

/**
 * The Robot Debug Console of a debug session. A line entered while the run is paused is evaluated in the selected frame
 * as the debugger's REPL does: a single variable shows its value, anything else runs as a keyword call. The console
 * exists before the connection to the debugger, so it sends through the debugger of the selected frame.
 */
internal class RobotCodeDebugConsole(private val session: XDebugSession) : Disposable {
    val console = LanguageConsoleImpl(session.project, RobotCodeBundle.message("debugger.console.title"), RobotFrameworkLanguage)

    init {
        Disposer.register(this, console)
        console.file.putUserData(DEBUGGER_EXPRESSION_FILE, true)
        val handler = object : BaseConsoleExecuteActionHandler(false) {
            override fun execute(text: String, console: LanguageConsoleView) {
                evaluate(text)
            }
        }
        ConsoleHistoryController(
            RootType.findByClass(RobotCodeDebugConsoleRootType::class.java), "robotcode-debug-console", console
        ).install()
        val executeAction = ConsoleExecuteAction(console, handler)
        executeAction.registerCustomShortcutSet(executeAction.shortcutSet, console.consoleEditor.component)
    }

    // the debugger runs keywords only for a paused run, so a line entered at another time is not sent
    private fun evaluate(text: String) {
        val frame = session.currentStackFrame as? RobotCodeStackFrame
        if (!session.isSuspended || frame == null) {
            console.print(RobotCodeBundle.message("debugger.console.notPaused") + "\n", ConsoleViewContentType.SYSTEM_OUTPUT)
            return
        }
        frame.debugServer.evaluate(EvaluateArguments().apply {
            expression = text
            frameId = frame.frame.id
            context = EvaluateArgumentsContext.REPL
        }).whenComplete { response, error ->
            if (error == null) {
                response.result?.takeIf { it.isNotEmpty() }?.let {
                    console.print(it + "\n", ConsoleViewContentType.NORMAL_OUTPUT)
                }
            } else {
                val cause = (error as? CompletionException)?.cause ?: error
                val message = (cause as? ResponseErrorException)?.let { messageOf(it.responseError) } ?: cause.toString()
                console.print(message + "\n", ConsoleViewContentType.ERROR_OUTPUT)
            }
        }
    }

    override fun dispose() {
    }
}
