package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.ui.SettingsEditorFragment
import com.intellij.openapi.fileChooser.FileChooser
import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory
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
import javax.swing.JComponent

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
private class RobotCodeTargetPanel(private val project: Project) {
    lateinit var pathsButton: JBRadioButton
    lateinit var selectionButton: JBRadioButton
    val pathsField = RawCommandLineEditor()
    val namesField = RawCommandLineEditor()

    val component: JComponent = panel {
        buttonsGroup {
            row(RobotCodeBundle.message("run.target.label")) {
                pathsButton = radioButton(RobotCodeBundle.message("run.target.paths")).component
                selectionButton = radioButton(RobotCodeBundle.message("run.target.selection")).component
            }
        }
        row {
            cell(pathsField).align(AlignX.FILL)
            button(RobotCodeBundle.message("run.target.paths.browse")) { addPaths() }
        }.visibleIf(pathsButton.selected).rowComment(RobotCodeBundle.message("run.target.paths.comment"))
        row {
            cell(namesField).align(AlignX.FILL)
        }.visibleIf(selectionButton.selected).rowComment(RobotCodeBundle.message("run.target.selection.comment"))
    }

    private fun addPaths() {
        val descriptor = FileChooserDescriptorFactory.createAllButJarContentsDescriptor()
        val files = FileChooser.chooseFiles(descriptor, project, null)
        pathsField.text = joinTargetEntries(parseTargetEntries(pathsField.text) + files.map { it.presentableUrl })
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
 * a "Robot Framework" section for the target.
 */
class RobotCodeRunConfigurationEditor(configuration: RobotCodeRunConfiguration) :
    AbstractPythonConfigurationFragmentedEditor<RobotCodeRunConfiguration>(configuration) {

    override fun customizeFragments(fragments: MutableList<SettingsEditorFragment<RobotCodeRunConfiguration, *>>) {
        // Robot Framework runs use RobotCode's debugger
        fragments.removeIf { it.id == "justMyCode" }

        val targetPanel = RobotCodeTargetPanel(runConfiguration.project)
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
    }
}
