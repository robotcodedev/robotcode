package dev.robotcode.robotcode4ij

import com.intellij.openapi.util.IconLoader

class RobotIcons {
    companion object {
        val Resource = IconLoader.findIcon("/images/resource.svg", Companion::class.java)!!
        val Suite = IconLoader.findIcon("/images/suite.svg", Companion::class.java)!!
        val RobotCode = IconLoader.findIcon("/images/robotcode.svg", Companion::class.java)!!
        val Robot = IconLoader.findIcon("/images/suite.robot", Companion::class.java)!!
    }
    
}
