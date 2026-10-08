package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.components.BaseState
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.SimplePersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.components.StoragePathMacros
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import com.intellij.util.execution.ParametersListUtil
import dev.robotcode.robotcode4ij.configuration.SimplePersistentStateComponentHelper.stringDelegate

/**
 * The settings of the current user for a project, kept in the project's workspace file and not shared through version
 * control.
 */
@Service(Service.Level.PROJECT)
@State(name = "RobotCodePersonalSettings", storages = [Storage(StoragePathMacros.WORKSPACE_FILE)])
class RobotCodePersonalConfiguration :
    SimplePersistentStateComponent<RobotCodePersonalConfiguration.PersonalState>(PersonalState()) {
    companion object {
        fun getInstance(project: Project): RobotCodePersonalConfiguration = project.service()
    }

    // The arguments are stored as the command lines the user typed.
    class PersonalState : BaseState() {
        var extraArgs by string()
        var languageServerExtraArgs by string()
    }

    var extraArgs by stringDelegate(PersonalState::extraArgs)
    var languageServerExtraArgs by stringDelegate(PersonalState::languageServerExtraArgs)

    val extraArgsList: List<String>
        get() = ParametersListUtil.parse(extraArgs)

    val languageServerExtraArgsList: List<String>
        get() = ParametersListUtil.parse(languageServerExtraArgs)
}
