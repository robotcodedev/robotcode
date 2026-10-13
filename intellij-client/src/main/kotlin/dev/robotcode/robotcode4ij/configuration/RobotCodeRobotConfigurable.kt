package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.fileChooser.FileChooser
import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory
import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.openapi.ui.TextFieldWithBrowseButton
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.ui.components.fields.ExtendableTextField
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.bindItem
import com.intellij.ui.dsl.builder.bindText
import com.intellij.ui.dsl.builder.panel
import com.intellij.ui.dsl.listCellRenderer.textListCellRenderer
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettings.RobotMode
import dev.robotcode.robotcode4ij.execution.chooserStart
import dev.robotcode.robotcode4ij.execution.pathRelativeTo
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged
import java.nio.file.Path

/**
 * The "Robot" page below the "Robot Framework" node: the settings of VS Code's settings category "Robot", which the
 * language server, test discovery and runs use on top of `robot.toml`.
 */
class RobotCodeRobotConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.robot.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.robot"
) {

    private val settings = RobotCodeProjectConfiguration.getInstance(project)

    private lateinit var dialogPanel: DialogPanel

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        val base = project.basePath?.let { Path.of(it) }
        dialogPanel = panel {
            row(RobotCodeBundle.message("settings.robot.args")) {
                commandLineField(settings::robotArgs)
            }.rowComment(RobotCodeBundle.message("settings.robot.args.comment"))
            row(RobotCodeBundle.message("settings.robot.paths")) {
                pathListField(
                    settings::robotPaths, project, { FileChooserDescriptorFactory.multiFilesOrDirs() },
                    RobotCodeBundle.message("run.target.paths.browse")
                )
            }.rowComment(RobotCodeBundle.message("settings.robot.paths.comment"))
            row(RobotCodeBundle.message("settings.robot.pythonPath")) {
                pathListField(
                    settings::robotPythonPath, project, { FileChooserDescriptorFactory.multiFilesOrDirs() },
                    RobotCodeBundle.message("run.target.paths.browse")
                )
            }.rowComment(RobotCodeBundle.message("settings.robot.pythonPath.comment"))
            row(RobotCodeBundle.message("settings.robot.env")) {
                nameValueTable(settings::robotEnv)
            }.rowComment(RobotCodeBundle.message("settings.robot.env.comment"))
            row(RobotCodeBundle.message("settings.robot.languages")) {
                listField(settings::robotLanguages)
            }.rowComment(RobotCodeBundle.message("settings.robot.languages.comment"))
            row(RobotCodeBundle.message("settings.robot.variables")) {
                nameValueTable(settings::robotVariables)
            }.rowComment(RobotCodeBundle.message("settings.robot.variables.comment"))
            row(RobotCodeBundle.message("settings.robot.variableFiles")) {
                pathListField(
                    settings::robotVariableFiles, project, { FileChooserDescriptorFactory.multiFiles() },
                    RobotCodeBundle.message("run.options.variableFiles.add")
                )
            }.rowComment(RobotCodeBundle.message("settings.robot.variableFiles.comment"))
            row(RobotCodeBundle.message("settings.robot.outputDir")) {
                // as the output directory of the run configuration
                val field = ExtendableTextField()
                val chooser = TextFieldWithBrowseButton(field) {
                    val files = LocalFileSystem.getInstance()
                    val start = chooserStart(field.text, base)?.let { files.findFileByNioFile(it) }
                        ?: base?.let { files.findFileByNioFile(it) }
                    FileChooser.chooseFile(FileChooserDescriptorFactory.singleDir(), project, start)?.let {
                        field.text = pathRelativeTo(it.toNioPath(), base)
                    }
                }
                cell(chooser).align(AlignX.FILL).bindText(settings::robotOutputDir)
            }.rowComment(RobotCodeBundle.message("settings.robot.outputDir.comment"))
            row(RobotCodeBundle.message("settings.robot.mode")) {
                comboBox(RobotMode.entries, textListCellRenderer<RobotMode?> { it?.let(::label) })
                    .bindItem(
                        { choiceOf<RobotMode>(settings.robotMode) },
                        { settings.robotMode = (it ?: RobotMode.DEFAULT).value }
                    )
            }.rowComment(RobotCodeBundle.message("settings.robot.mode.comment"))
        }
        return dialogPanel
    }

    override fun apply() {
        dialogPanel.checkValues()
        super.apply()
        // shows the stored values as the fields write them, for example the list entries
        reset()
        // the restart manager decides whether the change needs a restart or a discovery
        project.publishRobotCodeSettingsChanged()
    }

    private fun label(mode: RobotMode): String {
        return when (mode) {
            RobotMode.DEFAULT -> RobotCodeBundle.message("settings.robot.mode.default")
            RobotMode.RPA -> RobotCodeBundle.message("settings.robot.mode.rpa")
            RobotMode.NORPA -> RobotCodeBundle.message("settings.robot.mode.norpa")
        }
    }
}
