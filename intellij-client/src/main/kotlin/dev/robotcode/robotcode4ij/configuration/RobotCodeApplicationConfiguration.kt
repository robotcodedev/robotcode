package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.components.BaseState
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.SimplePersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.components.service
import dev.robotcode.robotcode4ij.configuration.SimplePersistentStateComponentHelper.delegate

/**
 * The settings of the current user that apply to all projects, kept in the IDE's configuration like VS Code's settings
 * of the scope `application`.
 */
@Service(Service.Level.APP)
@State(name = "RobotCodeApplicationSettings", storages = [Storage("robotcode.xml")])
class RobotCodeApplicationConfiguration :
    SimplePersistentStateComponent<RobotCodeApplicationConfiguration.ApplicationState>(ApplicationState()) {
    companion object {
        fun getInstance(): RobotCodeApplicationConfiguration = service()
    }

    class ApplicationState : BaseState() {
        // announces a new version after an update, as VS Code's robotcode.showWhatsNewOnUpdate does
        var showWhatsNewOnUpdate by property(true)
    }

    var showWhatsNewOnUpdate by delegate(ApplicationState::showWhatsNewOnUpdate)
}
