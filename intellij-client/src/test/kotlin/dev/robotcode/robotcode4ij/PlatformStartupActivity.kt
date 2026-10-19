package dev.robotcode.robotcode4ij

import com.intellij.openapi.extensions.ExtensionPointName
import com.intellij.openapi.startup.ProjectActivity

/**
 * The startup activity of RobotCode as the platform created it, with the plugin descriptor handed over. Only this
 * extension is created, because creating all of them logs an error for old startup activities of other plugins.
 */
internal fun platformStartupActivity(): RobotCodePostStartupActivity? {
    return ExtensionPointName<ProjectActivity>("com.intellij.postStartupActivity")
        .findExtension(RobotCodePostStartupActivity::class.java)
}
