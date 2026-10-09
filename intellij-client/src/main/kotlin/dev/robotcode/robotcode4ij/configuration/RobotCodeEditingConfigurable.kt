package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.bindSelected
import com.intellij.ui.dsl.builder.bindText
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged

/**
 * The "Editing" page below the "Robot Framework" node: completion and inlay hints.
 */
class RobotCodeEditingConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.editing.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.editing"
) {

    private val settings = RobotCodeProjectConfiguration.getInstance(project)

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        return panel {
            group(RobotCodeBundle.message("settings.editing.completion")) {
                row {
                    checkBox(RobotCodeBundle.message("settings.editing.completion.filterDefaultLanguage"))
                        .bindSelected(settings::completionFilterDefaultLanguage)
                }.rowComment(RobotCodeBundle.message("settings.editing.completion.filterDefaultLanguage.comment"))
                row(RobotCodeBundle.message("settings.editing.completion.headerStyle")) {
                    textField().bindText(settings::completionHeaderStyle)
                }.rowComment(RobotCodeBundle.message("settings.editing.completion.headerStyle.comment"))
                row {
                    checkBox(RobotCodeBundle.message("settings.editing.completion.hidePrivateKeywords"))
                        .bindSelected(settings::completionHidePrivateKeywords)
                }.rowComment(RobotCodeBundle.message("settings.editing.completion.hidePrivateKeywords.comment"))
                row {
                    checkBox(RobotCodeBundle.message("settings.editing.completion.hideDeprecatedKeywords"))
                        .bindSelected(settings::completionHideDeprecatedKeywords)
                }.rowComment(RobotCodeBundle.message("settings.editing.completion.hideDeprecatedKeywords.comment"))
            }
            group(RobotCodeBundle.message("settings.editing.inlayHints")) {
                row {
                    checkBox(RobotCodeBundle.message("settings.editing.inlayHints.parameterNames"))
                        .bindSelected(settings::inlayHintsParameterNames)
                }.rowComment(RobotCodeBundle.message("settings.editing.inlayHints.parameterNames.comment"))
                row {
                    checkBox(RobotCodeBundle.message("settings.editing.inlayHints.namespaces"))
                        .bindSelected(settings::inlayHintsNamespaces)
                }.rowComment(RobotCodeBundle.message("settings.editing.inlayHints.namespaces.comment"))
                row {
                    comment(RobotCodeBundle.message("settings.editing.inlayHints.comment"))
                }
            }
        }
    }

    override fun apply() {
        super.apply()
        // the restart manager decides whether the change needs a restart or a discovery
        project.publishRobotCodeSettingsChanged()
    }
}
