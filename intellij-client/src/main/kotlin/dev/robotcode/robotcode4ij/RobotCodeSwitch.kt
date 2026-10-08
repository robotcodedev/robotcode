package dev.robotcode.robotcode4ij

import com.intellij.openapi.project.Project
import com.intellij.ui.EditorNotifications
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.editor.updateRobotCodeStatusBar
import dev.robotcode.robotcode4ij.lsp.langServerManager
import dev.robotcode.robotcode4ij.testing.testManger

/**
 * Whether "Disable extension" switches RobotCode off for the project.
 */
val Project.isRobotCodeDisabled: Boolean
    get() = !isDefault && RobotCodePersonalConfiguration.getInstance(this).disableExtension

/**
 * Checks or unchecks "Disable extension" and acts on it at once.
 */
fun Project.setRobotCodeDisabled(disabled: Boolean) {
    val settings = RobotCodePersonalConfiguration.getInstance(this)
    if (settings.disableExtension == disabled) {
        return
    }
    settings.disableExtension = disabled
    robotCodeSwitchChanged()
}

/**
 * Follows a change of "Disable extension": switched off, the language server stops and the run markers disappear;
 * switched on, RobotCode starts as when the project is opened.
 */
internal fun Project.robotCodeSwitchChanged() {
    if (isRobotCodeDisabled) {
        langServerManager.stop()
        testManger.clearTestItems()
    } else {
        langServerManager.enableForSession()
        robotCodeEnvironment.startAgain()
    }
    EditorNotifications.getInstance(this).updateAllNotifications()
    updateRobotCodeStatusBar()
}

/**
 * LSP4IJ enabled the server, for example from the Language Servers tool window, and starts it itself.
 */
internal fun Project.languageServerEnabled() {
    langServerManager.enableForSession()
    val settings = RobotCodePersonalConfiguration.getInstance(this)
    if (settings.disableExtension) {
        settings.disableExtension = false
        testManger.refreshDebounced()
        EditorNotifications.getInstance(this).updateAllNotifications()
        updateRobotCodeStatusBar()
    }
}
