package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged

/**
 * The "Language Server" page below the "Robot Framework" node. Its values are personal, so new projects do not get it.
 */
class RobotCodeLanguageServerConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.languageServer.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.languageserver"
) {

    private val personalSettings = RobotCodePersonalConfiguration.getInstance(project)

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        return panel {
            row(RobotCodeBundle.message("settings.languageServer.extraArgs")) {
                commandLineField(personalSettings::languageServerExtraArgs)
            }.rowComment(RobotCodeBundle.message("settings.languageServer.extraArgs.comment"))
        }
    }

    override fun apply() {
        super.apply()
        // the restart manager decides whether the change needs a restart
        project.publishRobotCodeSettingsChanged()
    }
}
