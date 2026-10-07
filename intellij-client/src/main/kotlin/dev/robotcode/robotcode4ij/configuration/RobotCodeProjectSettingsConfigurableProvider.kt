package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.components.BaseState
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.SimplePersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.components.service
import com.intellij.openapi.options.Configurable
import com.intellij.openapi.options.ConfigurableProvider
import com.intellij.openapi.project.Project
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.configuration.SimplePersistentStateComponentHelper.delegate
import dev.robotcode.robotcode4ij.configuration.SimplePersistentStateComponentHelper.stringDelegate
import javax.swing.JComponent


class RobotCodeProjectSettingsConfigurableProvider : ConfigurableProvider() {
    override fun createConfigurable(): Configurable {
        return RobotCodeProjectSettingsConfigurable()
    }
}


/**
 * The "Robot Framework" node under Languages & Frameworks. It has no settings of its own yet, so it has no content, and
 * the settings dialog lists its sub-pages on its page instead.
 */
class RobotCodeProjectSettingsConfigurable : Configurable {
    override fun getDisplayName(): String = RobotCodeBundle.message("settings.robotframework.displayName")

    override fun createComponent(): JComponent? = null

    override fun isModified(): Boolean = false

    override fun apply() {
    }
}

@Service(Service.Level.PROJECT) @State(name = "ProjectSettings", storages = [Storage("robotcodeSettings.xml")])
class RobotCodeProjectConfiguration :
    SimplePersistentStateComponent<RobotCodeProjectConfiguration.ProjectState>(ProjectState()) {
    companion object {
        fun getInstance(project: Project): RobotCodeProjectConfiguration = project.service()
    }

    class ProjectState : BaseState() {
        var completionFilterDefaultLanguage by property(defaultValue = false)
        var completionHeaderStyle by string()
        var completionHidePrivateKeywords by property(defaultValue = true)
        var completionHideDeprecatedKeywords by property(defaultValue = false)
        var inlayHintsParameterNames by property(defaultValue = false)
        var inlayHintsNamespaces by property(defaultValue = false)
    }

    var completionFilterDefaultLanguage by delegate(ProjectState::completionFilterDefaultLanguage)
    var completionHeaderStyle by stringDelegate(ProjectState::completionHeaderStyle)
    var completionHidePrivateKeywords by delegate(ProjectState::completionHidePrivateKeywords)
    var completionHideDeprecatedKeywords by delegate(ProjectState::completionHideDeprecatedKeywords)
    var inlayHintsParameterNames by delegate(ProjectState::inlayHintsParameterNames)
    var inlayHintsNamespaces by delegate(ProjectState::inlayHintsNamespaces)
}
