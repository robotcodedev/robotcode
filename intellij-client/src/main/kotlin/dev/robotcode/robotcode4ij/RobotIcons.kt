package dev.robotcode.robotcode4ij

import com.intellij.openapi.util.IconLoader
import com.intellij.ui.IconManager

class RobotIcons {
    companion object {
        @JvmField
        val Resource = IconManager.getInstance().getIcon("/images/resource.svg", Companion::class.java.classLoader)
        @JvmField
        val Suite = IconManager.getInstance().getIcon("/images/suite.svg", Companion::class.java.classLoader)
        @JvmField
        val RobotCode = IconManager.getInstance().getIcon("/images/robotcode.svg", Companion::class.java.classLoader)
        @JvmField
        val Robot = IconManager.getInstance().getIcon("/images/suite.robot", Companion::class.java.classLoader)
    }
    
}
