package dev.robotcode.robotcode4ij.actions

import com.intellij.execution.Executor
import com.intellij.execution.ProgramRunnerUtil
import com.intellij.execution.RunManager
import com.intellij.execution.RunnerAndConfigurationSettings
import com.intellij.execution.actions.ConfigurationContext
import com.intellij.execution.actions.RunConfigurationProducer
import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.lineMarker.ExecutorAction
import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.ui.popup.JBPopupFactory
import com.intellij.ui.dsl.listCellRenderer.textListCellRenderer
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.configuration.ProfileInfo
import dev.robotcode.robotcode4ij.configuration.ProfileList
import dev.robotcode.robotcode4ij.configuration.ProfileListResult
import dev.robotcode.robotcode4ij.configuration.profileListCache
import dev.robotcode.robotcode4ij.configuration.readProfileList
import dev.robotcode.robotcode4ij.execution.RobotCodeRunConfiguration
import dev.robotcode.robotcode4ij.execution.RobotCodeRunConfigurationProducer
import dev.robotcode.robotcode4ij.execution.RobotRunProfilesKind

internal const val RUN_WITH_PROFILE_ACTION_ID = "dev.robotcode.robotcode4ij.actions.RobotCodeRunWithProfileAction"
internal const val DEBUG_WITH_PROFILE_ACTION_ID = "dev.robotcode.robotcode4ij.actions.RobotCodeDebugWithProfileAction"

/**
 * The [gutterActions] of a run marker with "Run with Profile..." and "Debug with Profile..." right after the executor
 * actions, before the extra actions that the platform puts after them, such as "Modify Run Configuration...", and last
 * without executor actions.
 */
internal fun withProfileActions(gutterActions: Array<AnAction>): Array<AnAction> {
    val manager = ActionManager.getInstance()
    val profileActions =
        listOfNotNull(manager.getAction(RUN_WITH_PROFILE_ACTION_ID), manager.getAction(DEBUG_WITH_PROFILE_ACTION_ID))
    val lastExecutorAction = gutterActions.indexOfLast { it is ExecutorAction }
    val at = if (lastExecutorAction >= 0) lastExecutorAction + 1 else gutterActions.size
    return (gutterActions.take(at) + profileActions + gutterActions.drop(at)).toTypedArray()
}

/**
 * Runs or debugs what a context run of the same place runs, once, with a profile of `robot.toml` chosen in a popup.
 * The run gets a copy of the configuration the context yields, which the run manager does not know, so saved
 * configurations and later gutter runs stay as they are.
 */
abstract class RobotCodeWithProfileAction(private val executor: () -> Executor) : AnAction(), DumbAware {
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        val context = ConfigurationContext.getFromContext(e.dataContext, e.place)
        e.presentation.isEnabledAndVisible = e.project != null && fromContext(context) != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val context = ConfigurationContext.getFromContext(e.dataContext, e.place)
        val producer = RunConfigurationProducer.getInstance(RobotCodeRunConfigurationProducer::class.java)
        // an existing configuration with the same target, as a context run would reuse it, or a new one
        val settings = producer.findExistingConfiguration(context) ?: fromContext(context) ?: return
        val title = templatePresentation.text.removeSuffix("...")
        val list = profileList(project, title) ?: return
        if (list.profiles.isEmpty()) {
            val text = list.messages.joinToString("\n").ifEmpty { RobotCodeBundle.message("profiles.none") }
            Messages.showInfoMessage(project, text, title)
            return
        }
        val popups = JBPopupFactory.getInstance()
        popups.createPopupChooserBuilder(list.profiles)
            .setTitle(RobotCodeBundle.message("run.withProfile.chooser"))
            .setRenderer(textListCellRenderer<ProfileInfo?> { profile ->
                profile?.let { if (it.description.isBlank()) it.name else "${it.name} – ${it.description}" }
            })
            .setItemChosenCallback { run(project, settings, it.name) }
            .createPopup()
            .show(popups.guessBestPopupLocation(this, e))
    }

    private fun fromContext(context: ConfigurationContext): RunnerAndConfigurationSettings? {
        return context.configurationsFromContext
            ?.firstOrNull { it.isProducedBy(RobotCodeRunConfigurationProducer::class.java) }
            ?.configurationSettings
    }

    // the cached list, or the list read now with a progress that can be cancelled
    private fun profileList(project: Project, title: String): ProfileList? {
        project.profileListCache.cached?.let { return it }
        return when (val result = project.readProfileList(listOf())) {
            is ProfileListResult.Read -> result.list.also { project.profileListCache.store(it) }
            is ProfileListResult.Error -> {
                Messages.showErrorDialog(project, result.message, title)
                null
            }

            null -> null
        }
    }

    private fun run(project: Project, settings: RunnerAndConfigurationSettings, profile: String) {
        val configuration = settings.configuration.clone() as? RobotCodeRunConfiguration ?: return
        configuration.options.profilesKind = RobotRunProfilesKind.CUSTOM
        configuration.options.profiles = mutableListOf(profile)
        configuration.name = RobotCodeBundle.message("run.withProfile.name", settings.name, profile)
        val copy = RunManager.getInstance(project).createConfiguration(configuration, settings.factory)
        ProgramRunnerUtil.executeConfiguration(copy, executor())
    }
}

class RobotCodeRunWithProfileAction : RobotCodeWithProfileAction({ DefaultRunExecutor.getRunExecutorInstance() })

class RobotCodeDebugWithProfileAction :
    RobotCodeWithProfileAction({ DefaultDebugExecutor.getDebugExecutorInstance() })
