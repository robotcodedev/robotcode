package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory
import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.openapi.ui.TextFieldWithBrowseButton
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.bindSelected
import com.intellij.ui.dsl.builder.bindText
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged

/**
 * The "Robocop" page below the "Robot Framework" node.
 */
class RobotCodeRobocopConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.robocop.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.robocop"
) {

    private val settings = RobotCodeProjectConfiguration.getInstance(project)

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        return panel {
            row {
                checkBox(RobotCodeBundle.message("settings.robocop.enabled"))
                    .bindSelected(settings::robocopEnabled)
            }.rowComment(RobotCodeBundle.message("settings.robocop.enabled.comment"))
            row(RobotCodeBundle.message("settings.robocop.configFile")) {
                val field = TextFieldWithBrowseButton().apply {
                    addBrowseFolderListener(project, FileChooserDescriptorFactory.singleFile())
                }
                // stored as entered, as in VS Code; the language server and Robocop resolve it
                cell(field)
                    .align(AlignX.FILL)
                    .bindText(settings::robocopConfigFile)
            }.rowComment(RobotCodeBundle.message("settings.robocop.configFile.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.robocop.ignoreGitDir"))
                    .bindSelected(settings::robocopIgnoreGitDir)
            }.rowComment(RobotCodeBundle.message("settings.robocop.ignoreGitDir.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.robocop.ignoreFileConfig"))
                    .bindSelected(settings::robocopIgnoreFileConfig)
            }.rowComment(RobotCodeBundle.message("settings.robocop.ignoreFileConfig.comment"))
        }
    }

    override fun apply() {
        super.apply()
        // the restart manager decides whether the change needs a restart or a discovery
        project.publishRobotCodeSettingsChanged()
    }
}
