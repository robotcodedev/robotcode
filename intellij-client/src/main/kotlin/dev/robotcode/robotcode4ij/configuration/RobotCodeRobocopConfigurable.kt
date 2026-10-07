package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory
import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.openapi.ui.TextFieldWithBrowseButton
import com.intellij.openapi.ui.ValidationInfo
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.bindSelected
import com.intellij.ui.dsl.builder.bindText
import com.intellij.ui.dsl.builder.panel
import com.intellij.ui.layout.ValidationInfoBuilder
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.restartAll
import java.nio.file.InvalidPathException
import java.nio.file.Path
import kotlin.io.path.isRegularFile

/**
 * The "Robocop" page below the "Robot Framework" node.
 */
class RobotCodeRobocopConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.robocop.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.robocop"
) {

    private val settings = RobotCodeProjectConfiguration.getInstance(project)

    private val projectDir = project.basePath?.let { Path.of(it) }

    private lateinit var dialogPanel: DialogPanel

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        dialogPanel = panel {
            row {
                checkBox(RobotCodeBundle.message("settings.robocop.enabled"))
                    .bindSelected(settings::robocopEnabled)
            }.rowComment(RobotCodeBundle.message("settings.robocop.enabled.comment"))
            row(RobotCodeBundle.message("settings.robocop.configFile")) {
                val field = TextFieldWithBrowseButton().apply {
                    addBrowseFolderListener(project, FileChooserDescriptorFactory.singleFile())
                }
                cell(field)
                    .align(AlignX.FILL)
                    .bindText(
                        { settings.robocopConfigFile },
                        { text ->
                            settings.robocopConfigFile = if (text.isBlank()) {
                                ""
                            } else {
                                resolveRobocopConfigFile(text, projectDir)?.toString() ?: text.trim()
                            }
                        }
                    )
                    .validationOnInput { checkConfigFile(it.text) }
                    .validationOnApply { checkConfigFile(it.text) }
            }.rowComment(RobotCodeBundle.message("settings.robocop.configFile.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.robocop.ignoreGitDir"))
                    .bindSelected(settings::robocopIgnoreGitDir)
            }.rowComment(RobotCodeBundle.message("settings.robocop.ignoreGitDir.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.robocop.ignoreFileConfig"))
                    .bindSelected(settings::robocopIgnoreFileConfig)
            }.rowComment(RobotCodeBundle.message("settings.robocop.ignoreFileConfig.comment"))
        }
        return dialogPanel
    }

    override fun apply() {
        dialogPanel.checkValues()
        super.apply()
        // shows the configuration file as the absolute path that is stored
        reset()
        project.restartAll()
    }

    private fun ValidationInfoBuilder.checkConfigFile(text: String): ValidationInfo? {
        return if (isExistingRobocopConfigFile(text, projectDir)) {
            null
        } else {
            error(RobotCodeBundle.message("settings.robocop.configFile.missing"))
        }
    }
}

/**
 * The absolute path of the Robocop configuration file in [text], with a relative path resolved against [projectDir],
 * or null when [text] is not a valid path.
 */
internal fun resolveRobocopConfigFile(text: String, projectDir: Path?): Path? {
    val path = try {
        Path.of(text.trim())
    } catch (_: InvalidPathException) {
        return null
    }
    return (projectDir?.resolve(path) ?: path).normalize()
}

/**
 * Whether [text] is empty, which means no configuration file is set, or names a file that exists.
 */
internal fun isExistingRobocopConfigFile(text: String, projectDir: Path?): Boolean {
    return text.isBlank() || resolveRobocopConfigFile(text, projectDir)?.isRegularFile() == true
}
