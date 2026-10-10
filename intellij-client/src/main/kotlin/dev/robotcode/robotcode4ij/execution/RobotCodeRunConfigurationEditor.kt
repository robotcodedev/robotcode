package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.ui.SettingsEditorFragment
import com.intellij.ide.macro.MacrosDialog
import com.intellij.openapi.fileChooser.FileChooser
import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory
import com.intellij.openapi.options.ConfigurationException
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.ValidationInfo
import com.intellij.ui.RawCommandLineEditor
import com.intellij.ui.components.JBRadioButton
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.panel
import com.intellij.ui.layout.selected
import com.intellij.util.execution.ParametersListUtil
import com.jetbrains.python.run.configuration.AbstractPythonConfigurationFragmentedEditor
import dev.robotcode.robotcode4ij.RobotCodeBundle
import java.nio.file.InvalidPathException
import java.nio.file.Path
import javax.swing.JComponent
import kotlin.io.path.invariantSeparatorsPathString

/**
 * The entries of a target field: separated by spaces and in quotes when they contain spaces, as in IntelliJ's argument
 * fields. Blank entries are left out.
 */
internal fun parseTargetEntries(text: String): List<String> {
    return ParametersListUtil.parse(text).map { it.trim() }.filter { it.isNotEmpty() }
}

internal fun joinTargetEntries(entries: List<String>): String {
    return ParametersListUtil.join(entries)
}

/**
 * The text that the editor adds for a chosen file or folder: its path relative to the working directory [base], with
 * forward slashes, when it lies inside it, else its absolute path.
 */
internal fun pathRelativeTo(file: Path, base: Path?): String {
    val absolute = file.toAbsolutePath().normalize()
    val directory = base?.toAbsolutePath()?.normalize()
    if (directory == null || !absolute.startsWith(directory)) {
        return file.toString()
    }
    return directory.relativize(absolute).invariantSeparatorsPathString.ifEmpty { "." }
}

/**
 * Where the folder chooser of a path field starts: the path in [text], relative to the working directory [base], or
 * [base] itself while the field is empty or holds a macro.
 */
internal fun chooserStart(text: String, base: Path?): Path? {
    val value = text.trim()
    if (value.isEmpty() || '$' in value) {
        return base
    }
    val path = try {
        Path.of(value)
    } catch (_: InvalidPathException) {
        return base
    }
    return if (path.isAbsolute) path else base?.resolve(path)
}

/**
 * The items of a "Tests and suites" target for the full [names]. A name that is already stored keeps its item; a new
 * name becomes an item with only that name.
 */
internal fun selectionItemsFromNames(
    names: List<String>, stored: List<RobotRunSelectionItem>
): List<RobotRunSelectionItem> {
    val byName = stored.associateBy { it.name }
    return names.map { it.trim() }.filter { it.isNotEmpty() }.distinct().map { name ->
        RobotRunSelectionItem().apply {
            val item = byName[name]
            if (item != null) copyFrom(item) else this.name = name
        }
    }
}

/**
 * The "Robot Framework" section of the run configuration editor: what the configuration runs.
 */
private class RobotCodeTargetPanel(
    private val project: Project, hasModule: () -> Boolean, private val workingDirectory: () -> Path?
) {
    lateinit var pathsButton: JBRadioButton
    lateinit var selectionButton: JBRadioButton
    val pathsField = RawCommandLineEditor()
    val namesField = RawCommandLineEditor()

    init {
        addMacros(pathsField.editorField, MacrosDialog.Filters.ANY_PATH, hasModule)
    }

    val component: JComponent = panel {
        buttonsGroup {
            row(RobotCodeBundle.message("run.target.label")) {
                pathsButton = radioButton(RobotCodeBundle.message("run.target.paths")).component
                selectionButton = radioButton(RobotCodeBundle.message("run.target.selection")).component
            }
        }
        // the comment comes before visibleIf, so that it is hidden with its row
        row {
            cell(pathsField).align(AlignX.FILL).resizableColumn()
            button(RobotCodeBundle.message("run.target.paths.browse")) { addPaths() }
        }.rowComment(RobotCodeBundle.message("run.target.paths.comment")).visibleIf(pathsButton.selected)
        row {
            cell(namesField).align(AlignX.FILL)
        }.rowComment(RobotCodeBundle.message("run.target.selection.comment")).visibleIf(selectionButton.selected)
    }

    private fun addPaths() {
        val descriptor = FileChooserDescriptorFactory.createAllButJarContentsDescriptor()
        val files = FileChooser.chooseFiles(descriptor, project, null)
        val paths = files.map { pathRelativeTo(it.toNioPath(), workingDirectory()) }
        pathsField.text = joinTargetEntries(parseTargetEntries(pathsField.text) + paths)
    }

    fun reset(options: RobotCodeRunConfigurationOptions) {
        when (options.targetKind) {
            RobotRunTargetKind.PATHS -> pathsButton.isSelected = true
            RobotRunTargetKind.SELECTION -> selectionButton.isSelected = true
        }
        pathsField.text = joinTargetEntries(options.targetPaths)
        namesField.text = joinTargetEntries(options.selection.mapNotNull { it.name })
    }

    fun applyTo(options: RobotCodeRunConfigurationOptions) {
        options.targetKind = if (selectionButton.isSelected) RobotRunTargetKind.SELECTION else RobotRunTargetKind.PATHS
        options.targetPaths = parseTargetEntries(pathsField.text).toMutableList()
        val names = parseTargetEntries(namesField.text)
        options.selection = selectionItemsFromNames(names, options.selection).toMutableList()
    }

    // an empty list of files and folders is a target of its own; an empty selection runs the configured paths as well
    fun validate(options: RobotCodeRunConfigurationOptions): List<ValidationInfo> {
        if (options.targetKind == RobotRunTargetKind.SELECTION && options.selection.isEmpty()) {
            val message = RobotCodeBundle.message("run.target.selection.empty")
            return listOf(ValidationInfo(message, namesField.textField).asWarning())
        }
        return listOf()
    }
}

/**
 * PyCharm's run configuration editor with "Modify options", without the option of PyCharm's Python debugger, and with
 * a "Robot Framework" section for the target and the Robot Framework options.
 */
class RobotCodeRunConfigurationEditor(configuration: RobotCodeRunConfiguration) :
    AbstractPythonConfigurationFragmentedEditor<RobotCodeRunConfiguration>(configuration) {

    override fun customizeFragments(fragments: MutableList<SettingsEditorFragment<RobotCodeRunConfiguration, *>>) {
        // Robot Framework runs use RobotCode's debugger
        fragments.removeIf { it.id == "justMyCode" }

        val hasModule = { runConfiguration.module != null }
        // the working directory as the editor shows it, also before Apply; runs start in it
        val workingDirectory = {
            val configuration = runConfiguration.clone() as RobotCodeRunConfiguration
            try {
                applyEditorTo(configuration)
            } catch (_: ConfigurationException) {
                // the stored values stand in for fields that cannot be applied
            }
            try {
                Path.of(configuration.workingDirectorySafe)
            } catch (_: InvalidPathException) {
                null
            }
        }
        val targetPanel = RobotCodeTargetPanel(runConfiguration.project, hasModule, workingDirectory)
        val target = SettingsEditorFragment<RobotCodeRunConfiguration, JComponent>(
            "robotcode.target",
            RobotCodeBundle.message("run.target.name"),
            RobotCodeBundle.message("run.target.group"),
            targetPanel.component,
            { configuration, _ -> targetPanel.reset(configuration.options) },
            { configuration, _ -> targetPanel.applyTo(configuration.options) },
            { true }
        )
        target.isRemovable = false
        target.setValidation { configuration -> targetPanel.validate(configuration.options) }
        addToFragmentsBeforeEditors(fragments, target)
        // in this order after the target; inserting each before PyCharm's editors would reverse them
        val options = robotOptionFragments(runConfiguration.project, hasModule, workingDirectory)
        fragments.addAll(fragments.indexOf(target) + 1, options)
    }
}
