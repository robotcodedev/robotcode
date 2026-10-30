package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.ExecutionResult
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.runners.ExecutionUtil
import com.intellij.execution.ui.ConsoleView
import com.intellij.openapi.util.Key
import com.intellij.xdebugger.XDebugSession
import com.jetbrains.python.debugger.PyDebugProcess
import com.jetbrains.python.debugger.PyDebugRunner
import com.jetbrains.python.parser.icons.PythonParserIcons
import com.jetbrains.python.run.PythonCommandLineState
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.execution.RobotCodeProcessHandler
import dev.robotcode.robotcode4ij.execution.RobotCodeRunConfiguration
import dev.robotcode.robotcode4ij.execution.RobotCodeRunProfileState
import java.net.ServerSocket
import java.util.concurrent.CompletableFuture

/** The run's state, which the Python environment of a run with "Attach Python" shares with the run's environment. */
internal val PYTHON_SESSION_RUN_STATE: Key<RobotCodeRunProfileState> = Key.create("ROBOTCODE_PYTHON_SESSION_RUN_STATE")

/** The run's environment, from the Python environment of a run with "Attach Python". */
internal val PYTHON_SESSION_RUN_ENVIRONMENT: Key<ExecutionEnvironment> =
    Key.create("ROBOTCODE_PYTHON_SESSION_RUN_ENVIRONMENT")

/**
 * The run profile of the Python environment of a run with "Attach Python": a copy of the run's [configuration], named
 * after the Python session, with PyCharm's Python icon and without before-launch tasks, because the ExecutionManager
 * runs them for the run's environment already. PyCharm's Python debug runner gives the session and its tab the copy's
 * name and icon.
 */
internal fun pythonSessionConfiguration(configuration: RobotCodeRunConfiguration): RobotCodeRunConfiguration {
    val copy = configuration.clone() as RobotCodeRunConfiguration
    copy.name = RobotCodeBundle.message("debugger.pythonSession.tabName", configuration.name)
    copy.sessionIcon = PythonParserIcons.PythonFile
    copy.beforeRunTasks = listOf()
    return copy
}

/**
 * PyCharm's Python debug runner for a Debug run with "Attach Python". [PyDebugRunner] starts the run under pydevd,
 * whatever PyCharm's Python debugger mode says, and creates the Python session; this subclass gives that session a
 * [RobotCodePythonSessionHandler] instead of the run's process handler, and hands the run's handler to [onRun] for the
 * Robot Framework session. It is not registered as a program runner; RobotCode's Debug runner makes it the runner of
 * the run's Python environment and starts that environment with [execute], which goes through the ExecutionManager.
 */
internal class RobotCodePythonDebugRunner(private val onRun: (ProcessHandler) -> Unit) : PyDebugRunner() {

    override fun getRunnerId(): String = "dev.robotcode.robotcode4ij.debugging.RobotCodePythonDebugRunner"

    // a rerun from the Python tab: the run's state has run once it has its test tree console, so the run's environment
    // starts again, with both sessions
    override fun execute(environment: ExecutionEnvironment) {
        val runEnvironment = environment.getUserData(PYTHON_SESSION_RUN_ENVIRONMENT)
        if (runEnvironment != null && environment.getUserData(PYTHON_SESSION_RUN_STATE)?.testTreeConsole != null) {
            ExecutionUtil.restart(runEnvironment)
            return
        }
        super.execute(environment)
    }

    override fun createDebugProcess(
        session: XDebugSession, serverSocket: ServerSocket, result: ExecutionResult, pyState: PythonCommandLineState
    ): PyDebugProcess = PyDebugProcess(
        session, serverSocket, result.executionConsole, pythonSessionHandler(result, onRun), pyState.isMultiprocessDebug
    )

    // the debugger in server mode, which PyCharm uses when its Python debugger settings ask for a fixed port
    override fun createDebugProcess(session: XDebugSession, serverPort: Int, result: ExecutionResult): PyDebugProcess =
        PyDebugProcess(session, result.executionConsole, pythonSessionHandler(result, onRun), "localhost", serverPort)
}

/**
 * The process handler of the Python session of a run with "Attach Python": a [RobotCodePythonSessionHandler] for the
 * run's handler in [result], which goes to [onRun] for the Robot Framework session. The run's Python debug console is
 * attached to it, because PyCharm switches that console to its Python prompt only while the console's process runs;
 * the stand-in writes no output, so the run's output stays in the test tree console.
 */
internal fun pythonSessionHandler(
    result: ExecutionResult, onRun: (ProcessHandler) -> Unit
): RobotCodePythonSessionHandler {
    val runHandler = result.processHandler
    onRun(runHandler)
    val settled = (runHandler as? RobotCodeProcessHandler)?.stopSettled ?: CompletableFuture.completedFuture(Unit)
    val handler = RobotCodePythonSessionHandler(runHandler, settled)
    (result.executionConsole as? ConsoleView)?.attachToProcess(handler)
    return handler
}
