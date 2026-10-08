package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.restartAll
import dev.robotcode.robotcode4ij.testing.testManger
import javax.swing.JLabel

/**
 * The "General" page below the "Robot Framework" node. Its values are personal, so new projects do not get it.
 */
class RobotCodeGeneralConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.general.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.general"
) {

    private val personalSettings = RobotCodePersonalConfiguration.getInstance(project)

    // the profile selection of the page, which Apply stores
    private var profiles: List<String> = personalSettings.profiles.toList()

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        lateinit var profilesLabel: JLabel
        fun showProfiles() {
            profilesLabel.text = profiles.joinToString(", ")
                .ifEmpty { RobotCodeBundle.message("settings.general.profiles.default") }
        }

        return panel {
            row(RobotCodeBundle.message("settings.general.extraArgs")) {
                commandLineField(personalSettings::extraArgs)
            }.rowComment(RobotCodeBundle.message("settings.general.extraArgs.comment"))
            row(RobotCodeBundle.message("settings.general.profiles")) {
                profilesLabel = label("").component
                showProfiles()
                button(RobotCodeBundle.message("settings.general.profiles.select")) {
                    project.chooseProfiles(profiles) { profiles = it }?.let { profiles = it }
                    showProfiles()
                }
            }.rowComment(RobotCodeBundle.message("settings.general.profiles.comment"))

            onIsModified { profiles != personalSettings.profiles }
            onReset {
                profiles = personalSettings.profiles.toList()
                showProfiles()
            }
            onApply { personalSettings.profiles = profiles.toMutableList() }
        }
    }

    override fun apply() {
        val extraArgs = personalSettings.extraArgs
        val profilesBefore = personalSettings.profiles.toList()
        super.apply()
        // the language server reads the profiles only when it starts; the restart runs discovery as well
        if (personalSettings.profiles != profilesBefore) {
            project.restartAll()
        } else if (personalSettings.extraArgs != extraArgs) {
            // the language server does not use them
            project.testManger.refreshDebounced()
        }
    }
}
