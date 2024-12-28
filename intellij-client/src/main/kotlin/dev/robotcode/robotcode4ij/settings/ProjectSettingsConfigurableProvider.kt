package dev.robotcode.robotcode4ij.settings

import com.google.gson.GsonBuilder
import com.google.gson.JsonElement
import com.intellij.openapi.components.BaseState
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.SimplePersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.components.service
import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.options.Configurable
import com.intellij.openapi.options.ConfigurableProvider
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.bindSelected
import com.intellij.ui.dsl.builder.bindText
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.lsp.langServerManager
import dev.robotcode.robotcode4ij.settings.SimplePersistentStateComponentHelper.delegate
import dev.robotcode.robotcode4ij.settings.SimplePersistentStateComponentHelper.stringDelegate


class ProjectSettingsConfigurableProvider(private val project: Project) : ConfigurableProvider() {
    override fun createConfigurable(): Configurable {
        return ProjectSettingsConfigurable(project)
    }
    
    override fun canCreateConfigurable(): Boolean {
        return super.canCreateConfigurable()
    }
}


class ProjectSettingsConfigurable(private val project: Project) : BoundSearchableConfigurable(
    "Robot Framework", "robotcode.robotframework.settings"
) {
    
    private val settings = ProjectSettings.getInstance(project)
    
    override fun createPanel(): DialogPanel {
        return panel {
            row {
                text("!!!! ATTENTION !!! this is work in progress")
            }
            group("Robot") {
                row {
                    expandableTextField().align(AlignX.FILL) .label("Arguments")
                }.rowComment("Additional arguments to pass to the <b>robot</b> command.")
                row {
                    comboBox(listOf("default", "rpa", "norpa")).label("Mode")
                }.rowComment("Specifies robot execution mode. Corresponds to the `--rpa` or `--norpa` option of __robot__.")
            }
            group("Editing") {
                // TODO: not supported in IntelliJ
                // group("Editor") {
                //     row {
                //         checkBox("4 Spaces Tab").bindSelected(settings::editor4SpacesTab)
                //     }.rowComment("If actived insert 4 spaces if TAB is pressed.")
                // }
                group("Completion") {
                    row {
                        checkBox("Filter Default Language").bindSelected(settings::completionFilterDefaultLanguage)
                    }.rowComment("Filter default language (English) for completion if there is another language defined.")
                    row {
                        textField().bindText(settings::completionHeaderStyle).label("Header Style")
                    }.rowComment("Defines the header style format. If not defined ```*** {name} ***``` is used.")
                }
                group("Inlay Hints") {
                    row {
                        checkBox("Parameter Names").bindSelected(settings::inlayHintsParameterNames)
                    }.rowComment(
                        "Enable/disable inlay hints for parameter names."
                    )
                    row {
                        checkBox("Namespaces").bindSelected(settings::inlayHintsNamespaces)
                    }.rowComment(
                        "Enable/disable inlay hints for namespaces."
                    )
                }
            }
        }
    }
    
    override fun apply() {
        super.apply()
        project.langServerManager.restart()
    }
}

@Service(Service.Level.PROJECT) @State(name = "ProjectSettings", storages = [Storage("robotcodeSettings.xml")])
class ProjectSettings : SimplePersistentStateComponent<ProjectSettings.ProjectState>(ProjectState()) {
    companion object {
        fun getInstance(project: Project): ProjectSettings = project.service()
    }
    
    fun asJson(): JsonElement {
        val builder = GsonBuilder().serializeNulls().setPrettyPrinting().create();
        
        val robotSettings = RobotCodeSettings()
        robotSettings.robotcode.inlayHints.parameterNames = state.inlayHintsParameterNames
        robotSettings.robotcode.inlayHints.namespaces = state.inlayHintsNamespaces
        
        val json = builder.toJsonTree(robotSettings)
        return json;
    }
    
    class ProjectState : BaseState() {
        // TODO var editor4SpacesTab by property(defaultValue = true)
        var completionFilterDefaultLanguage by property(defaultValue = false)
        var completionHeaderStyle by string()
        var inlayHintsParameterNames by property(defaultValue = false)
        var inlayHintsNamespaces by property(defaultValue = false)
    }
    
    // TODO var editor4SpacesTab by delegate(ProjectState::editor4SpacesTab)
    var completionFilterDefaultLanguage by delegate(ProjectState::completionFilterDefaultLanguage)
    var completionHeaderStyle by stringDelegate(ProjectState::completionHeaderStyle)
    var inlayHintsParameterNames by delegate(ProjectState::inlayHintsParameterNames)
    var inlayHintsNamespaces by delegate(ProjectState::inlayHintsNamespaces)
}

data class InlayHints(
    var parameterNames: Boolean = false, var namespaces: Boolean = false
)

data class Completion(
    var filterDefaultLanguage: Boolean = false,
    var headerStyle: String? = null
)

data class All(
    var completion: Completion = Completion(),
    var inlayHints: InlayHints = InlayHints()
)

data class RobotCodeSettings(
    var robotcode: All = All()
)


    
