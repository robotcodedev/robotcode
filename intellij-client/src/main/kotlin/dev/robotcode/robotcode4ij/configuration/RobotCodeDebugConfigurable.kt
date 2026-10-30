package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.bindSelected
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.RobotCodeBundle

/**
 * The "Debug" page below the "Robot Framework" node: the settings of VS Code's settings category "Debug" that the runs
 * of Robot Framework run configurations use unless a configuration sets its own. Runs read them when they start, so
 * applying them restarts nothing.
 */
class RobotCodeDebugConfigurable(project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.debug.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.debug"
) {

    private val settings = RobotCodeProjectConfiguration.getInstance(project)

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        return panel {
            row(RobotCodeBundle.message("settings.debug.launchWrapper")) {
                commandLineField(settings::debugLaunchWrapper)
            }.rowComment(RobotCodeBundle.message("settings.debug.launchWrapper.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.debug.outputMessages"))
                    .bindSelected(settings::debugOutputMessages)
            }.rowComment(RobotCodeBundle.message("settings.debug.outputMessages.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.debug.outputLog")).bindSelected(settings::debugOutputLog)
            }.rowComment(RobotCodeBundle.message("settings.debug.outputLog.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.debug.outputTimestamps"))
                    .bindSelected(settings::debugOutputTimestamps)
            }.rowComment(RobotCodeBundle.message("settings.debug.outputTimestamps.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.debug.attachPython"))
                    .bindSelected(settings::debugAttachPython)
            }.rowComment(RobotCodeBundle.message("settings.debug.attachPython.comment"))
            row {
                comment(RobotCodeBundle.message("settings.runDefaults.comment"))
            }
        }
    }
}
