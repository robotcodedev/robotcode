package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.options.Configurable
import com.intellij.openapi.options.SearchableConfigurable
import com.intellij.openapi.options.ShowSettingsUtil
import com.intellij.openapi.project.Project
import java.util.function.Predicate

/**
 * Opens the Python Interpreter settings of the project, found by the id of the page, which does not change with the
 * language of the IDE.
 */
class RobotCodeConfigurePythonInterpreterAction : AnAction() {
    companion object {
        private const val PYTHON_INTERPRETER_PAGE = "com.jetbrains.python.configuration.PyActiveSdkModuleConfigurable"

        fun showPythonInterpreterSettings(project: Project) {
            val predicate = Predicate<Configurable> { it is SearchableConfigurable && it.id == PYTHON_INTERPRETER_PAGE }
            ShowSettingsUtil.getInstance().showSettingsDialog(project, predicate, null)
        }
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        e.project?.let { showPythonInterpreterSettings(it) }
    }
}
