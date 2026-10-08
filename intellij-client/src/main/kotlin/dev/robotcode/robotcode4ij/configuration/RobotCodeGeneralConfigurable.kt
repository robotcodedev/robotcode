package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.testing.testManger

/**
 * The "General" page below the "Robot Framework" node. Its values are personal, so new projects do not get it.
 */
class RobotCodeGeneralConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.general.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.general"
) {

    private val personalSettings = RobotCodePersonalConfiguration.getInstance(project)

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        return panel {
            row(RobotCodeBundle.message("settings.general.extraArgs")) {
                commandLineField(personalSettings::extraArgs)
            }.rowComment(RobotCodeBundle.message("settings.general.extraArgs.comment"))
        }
    }

    override fun apply() {
        val extraArgs = personalSettings.extraArgs
        super.apply()
        // the language server does not use them
        if (personalSettings.extraArgs != extraArgs) {
            project.testManger.refreshDebounced()
        }
    }
}
