package dev.robotcode.robotcode4ij

import com.intellij.openapi.util.IconLoader
import javax.swing.Icon

public class RobotIcons {
    companion object {
        val Resource: Icon? = IconLoader.findIcon("/images/robot.svg", RobotIcons.Companion::class.java);
        val Suite: Icon? = IconLoader.findIcon("/images/robot.svg", RobotIcons.Companion::class.java);
        val RobotCode: Icon? = IconLoader.findIcon("/images/robotcode.svg", RobotIcons.Companion::class.java);
    }
    
}
