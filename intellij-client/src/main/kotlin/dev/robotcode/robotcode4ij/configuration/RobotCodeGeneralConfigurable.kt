package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.bindItem
import com.intellij.ui.dsl.builder.bindSelected
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.ModuleChoice
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.editor.updateRobotCodeStatusBar
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import dev.robotcode.robotcode4ij.robotCodeSwitchChanged
import javax.swing.JLabel

/**
 * The "General" page below the "Robot Framework" node. Its values are personal, so new projects do not get it; "Show
 * whats new on update" applies to all projects.
 */
class RobotCodeGeneralConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.general.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.general"
) {

    private val personalSettings = RobotCodePersonalConfiguration.getInstance(project)
    private val applicationSettings = RobotCodeApplicationConfiguration.getInstance()

    // the profile selection of the page, which Apply stores
    private var profiles: List<String> = personalSettings.profiles.toList()

    // the modules with a Python interpreter, which the page offers while there are several
    private val pythonModules = project.robotCodeEnvironment.pythonModuleNames

    // the module that RobotCode uses now, or null while it waits for the choice
    private fun chosenModule(): String? {
        return (project.robotCodeEnvironment.moduleChoice as? ModuleChoice.Resolved)?.moduleName
    }

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        lateinit var profilesLabel: JLabel
        fun showProfiles() {
            profilesLabel.text = profiles.joinToString(", ")
                .ifEmpty { RobotCodeBundle.message("settings.general.profiles.default") }
        }

        return panel {
            row {
                checkBox(RobotCodeBundle.message("settings.general.disableExtension"))
                    .bindSelected(personalSettings::disableExtension)
            }.rowComment(RobotCodeBundle.message("settings.general.disableExtension.comment"))
            // the comment comes before visible, so that it is hidden with its row
            row(RobotCodeBundle.message("settings.general.pythonModule")) {
                comboBox(pythonModules).bindItem(
                    { chosenModule() },
                    { if (it != null && it != chosenModule()) personalSettings.pythonModule = it }
                )
            }.rowComment(RobotCodeBundle.message("settings.general.pythonModule.comment"))
                .visible(pythonModules.size > 1)
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
            row {
                checkBox(RobotCodeBundle.message("settings.general.showWhatsNewOnUpdate"))
                    .bindSelected(applicationSettings::showWhatsNewOnUpdate)
            }.rowComment(RobotCodeBundle.message("settings.general.showWhatsNewOnUpdate.comment"))

            onIsModified { profiles != personalSettings.profiles }
            onReset {
                profiles = personalSettings.profiles.toList()
                showProfiles()
            }
            onApply { personalSettings.profiles = profiles.toMutableList() }
        }
    }

    override fun apply() {
        val disabled = personalSettings.disableExtension
        val profilesBefore = personalSettings.profiles.toList()
        val moduleBefore = personalSettings.pythonModule
        super.apply()
        if (personalSettings.profiles != profilesBefore) {
            project.updateRobotCodeStatusBar()
        }
        // switched on again, RobotCode starts with the other values of the page, and switched off, nothing restarts
        if (personalSettings.disableExtension != disabled) {
            project.robotCodeSwitchChanged()
        }
        // the restart manager decides whether the change needs a restart or a discovery, and the environment follows
        // another module
        if (personalSettings.disableExtension == disabled || personalSettings.pythonModule != moduleBefore) {
            project.publishRobotCodeSettingsChanged()
        }
    }
}
