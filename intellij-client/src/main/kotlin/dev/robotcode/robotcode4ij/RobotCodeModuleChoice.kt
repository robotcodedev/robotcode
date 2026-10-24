package dev.robotcode.robotcode4ij

import com.intellij.notification.Notification
import com.intellij.notification.NotificationAction
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.module.Module
import com.intellij.openapi.project.Project
import com.intellij.openapi.roots.ModuleRootManager
import com.intellij.openapi.util.text.StringUtil
import com.intellij.openapi.vfs.VfsUtilCore
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.search.FileTypeIndex
import com.intellij.ui.EditorNotifications
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import java.io.IOException

// The patterns are those of the VS Code client (ROBOT_PACKAGE, ROBOT_DEPENDENCY_IN_PYPROJECT and ROBOT_REQUIREMENT in
// languageclientsmanger.ts), so that both decide alike which folders are Robot Framework projects.

// the packages of Robot Framework and RobotCode, not the libraries and tools named after them
private const val ROBOT_PACKAGE = "(?:robotframework|robotcode)"

// a requirement string such as `"robotframework>=7.0"`, or a Poetry style key such as `robotframework = "^7.0"`
private val ROBOT_DEPENDENCY_IN_PYPROJECT = Regex(
    """["']\s*$ROBOT_PACKAGE\s*(?:\[[^\]]*\])?\s*(?:[<>=!~;@]|["'])|^\s*["']?$ROBOT_PACKAGE["']?\s*=""",
    setOf(RegexOption.IGNORE_CASE, RegexOption.MULTILINE)
)

private val ROBOT_REQUIREMENT = Regex(
    """^\s*$ROBOT_PACKAGE\s*(?:\[[^\]]*\])?\s*(?:[<>=!~;@#]|$)""",
    setOf(RegexOption.IGNORE_CASE, RegexOption.MULTILINE)
)

private val COMMENT_LINE = Regex("""^\s*#.*$""", RegexOption.MULTILINE)

/** Whether the text of a `pyproject.toml` depends on Robot Framework or RobotCode, in a line that is no comment. */
internal fun pyprojectDependsOnRobot(text: String): Boolean {
    return ROBOT_DEPENDENCY_IN_PYPROJECT.containsMatchIn(text.replace(COMMENT_LINE, ""))
}

/** Whether the text of a `requirements.txt` requires Robot Framework or RobotCode. */
internal fun requirementsDependOnRobot(text: String): Boolean = ROBOT_REQUIREMENT.containsMatchIn(text)

/**
 * Whether [module] is a Robot Framework project, as the VS Code extension decides it for a workspace folder: a content
 * root with a `robot.toml` or `.robot.toml`, or with a `pyproject.toml` or `requirements.txt` that depends on Robot
 * Framework or RobotCode, or Robot Framework suite or resource files in the module. It reads the indexes, so it runs in
 * a read action in smart mode.
 */
internal fun isRobotFrameworkModule(module: Module): Boolean {
    if (ModuleRootManager.getInstance(module).contentRoots.any { isRobotFrameworkFolder(it) }) {
        return true
    }
    val scope = module.moduleContentScope
    return FileTypeIndex.containsFileOfType(RobotSuiteFileType, scope) ||
        FileTypeIndex.containsFileOfType(RobotResourceFileType, scope)
}

private fun isRobotFrameworkFolder(folder: VirtualFile): Boolean {
    if (!folder.isDirectory) {
        return false
    }
    fun text(name: String): String? {
        val file = folder.findChild(name)?.takeUnless { it.isDirectory } ?: return null
        return try {
            VfsUtilCore.loadText(file)
        } catch (_: IOException) {
            null
        }
    }
    return listOf("robot.toml", ".robot.toml").any { folder.findChild(it) != null } ||
        text("pyproject.toml")?.let { pyprojectDependsOnRobot(it) } == true ||
        text("requirements.txt")?.let { requirementsDependOnRobot(it) } == true
}

/**
 * The module whose Python interpreter RobotCode uses for the language server, test discovery, the profile list and new
 * run configurations.
 */
sealed class ModuleChoice {
    /** The module named [moduleName], or none when no module has a Python interpreter. */
    data class Resolved(val moduleName: String?) : ModuleChoice()

    /** Several modules have an interpreter, and the detection of the Robot Framework projects among them runs. */
    data object Detecting : ModuleChoice()

    /** Several modules are Robot Framework projects, and the user has not chosen one of [candidates] yet. */
    data class Waiting(val candidates: List<String>) : ModuleChoice()
}

/** A choice and the reason for it, for idea.log. */
internal data class ModuleResolution(val choice: ModuleChoice, val reason: String)

/**
 * The choice among [modules], the names of the modules that have a Python interpreter, in the order of the project. A
 * single module is used at once, and so is the module the user has chosen, [chosen]. Otherwise [detected], the Robot
 * Framework projects among the modules, decides, or null while the detection runs: exactly one is used, without any the
 * first module is used, and several wait for the user's choice.
 */
internal fun resolveModuleChoice(modules: List<String>, chosen: String?, detected: List<String>?): ModuleResolution {
    return when {
        modules.isEmpty() -> ModuleResolution(ModuleChoice.Resolved(null), "no module has a Python interpreter")
        modules.size == 1 -> ModuleResolution(
            ModuleChoice.Resolved(modules.single()), "it is the only module with a Python interpreter"
        )

        chosen != null && chosen in modules -> ModuleResolution(
            ModuleChoice.Resolved(chosen), "it is the module stored for the project"
        )

        detected == null -> ModuleResolution(
            ModuleChoice.Detecting, "the Robot Framework projects among the modules are not detected yet"
        )

        detected.size == 1 -> ModuleResolution(
            ModuleChoice.Resolved(detected.single()), "it is the only Robot Framework project among the modules"
        )

        detected.isEmpty() -> ModuleResolution(
            ModuleChoice.Resolved(modules.first()),
            "no module is a Robot Framework project, and it is the first module with a Python interpreter"
        )

        else -> ModuleResolution(ModuleChoice.Waiting(detected), "several modules are Robot Framework projects")
    }
}

// the request to choose stays until the user chooses a module or closes it
private const val MODULE_NOTIFICATION_GROUP = "RobotCode Module"

/** The request to choose one of [candidates], with an action for each. */
internal fun moduleChoiceNotification(project: Project, candidates: List<String>): Notification {
    val notification = NotificationGroupManager.getInstance().getNotificationGroup(MODULE_NOTIFICATION_GROUP)
        .createNotification(
            RobotCodeBundle.message("python.module.notification.title"),
            StringUtil.escapeXmlEntities(
                EnvironmentResult.ModuleNotChosen(candidates).messageFor(InterpreterOwner.PROJECT)
            ),
            NotificationType.WARNING
        )
    candidates.forEach { name ->
        notification.addAction(
            NotificationAction.createSimpleExpiring(RobotCodeBundle.message("python.module.use", name)) {
                project.useRobotCodeModule(name)
            }
        )
    }
    return notification
}

/**
 * Stores [moduleName] as the module whose interpreter RobotCode uses, as the actions of the request to choose do: the
 * request disappears, and the settings change starts RobotCode with the interpreter of the module.
 */
fun Project.useRobotCodeModule(moduleName: String) {
    RobotCodePersonalConfiguration.getInstance(this).pythonModule = moduleName
    robotCodeEnvironment.expireModuleChoiceNotification()
    EditorNotifications.getInstance(this).updateAllNotifications()
    publishRobotCodeSettingsChanged()
}

/**
 * Passes changes of the RobotCode settings to the environment, because they can hold another choice of the module.
 */
class RobotCodeModuleChoiceSettingsListener(private val project: Project) : RobotCodeSettingsListener {
    override fun settingsChanged() {
        if (!project.isDefault) {
            project.robotCodeEnvironment.settingsChanged()
        }
    }
}
