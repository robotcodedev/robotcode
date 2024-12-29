package dev.robotcode.robotcode4ij

import com.intellij.openapi.application.PathManager
import java.nio.file.Path

class BundledHelpers {
    companion object {
        val basePath: Path = PathManager.getPluginsDir().resolve("robotcode4ij").resolve("data")
        val bundledPath: Path = basePath.resolve("bundled")
        val toolPath: Path = bundledPath.resolve("tool")
        val robotCodePath: Path = toolPath.resolve("robotcode")
        val checkRobotVersion: Path = toolPath.resolve("utils").resolve("check_robot_version.py")
    }
}
