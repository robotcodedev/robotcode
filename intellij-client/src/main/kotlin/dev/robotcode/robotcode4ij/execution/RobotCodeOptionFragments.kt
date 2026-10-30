package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.ui.SettingsEditorFragment
import com.intellij.ide.macro.Macro
import com.intellij.ide.macro.MacrosDialog
import com.intellij.openapi.fileChooser.FileChooser
import com.intellij.openapi.fileChooser.FileChooserDescriptor
import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.ComboBox
import com.intellij.openapi.ui.TextFieldWithBrowseButton
import com.intellij.openapi.ui.ValidationInfo
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.ui.RawCommandLineEditor
import com.intellij.ui.TableUtil
import com.intellij.ui.ToolbarDecorator
import com.intellij.ui.components.JBTextField
import com.intellij.ui.components.fields.ExtendableTextField
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.Row
import com.intellij.ui.dsl.builder.panel
import com.intellij.ui.dsl.listCellRenderer.textListCellRenderer
import com.intellij.ui.layout.selectedValueIs
import com.intellij.ui.table.TableView
import com.intellij.util.ui.ColumnInfo
import com.intellij.util.ui.ElementProducer
import com.intellij.util.ui.ListTableModel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.configuration.chooseProfiles
import dev.robotcode.robotcode4ij.configuration.openOutputLabel
import dev.robotcode.robotcode4ij.configuration.profileListCache
import java.awt.event.ItemEvent
import java.nio.file.Path
import java.util.function.Predicate
import javax.swing.JComponent
import kotlin.reflect.KMutableProperty1

private typealias RobotFragment = SettingsEditorFragment<RobotCodeRunConfiguration, *>

/** Adds IntelliJ's "Insert Macros" to [field]. */
internal fun addMacros(field: ExtendableTextField, filter: Predicate<in Macro>, hasModule: () -> Boolean) {
    MacrosDialog.addMacroSupport(field, filter) { hasModule() }
}

/** A row of the variables table. */
internal class RobotVariable(var name: String, var value: String)

/** An editable column of the variables table. */
internal class VariableColumn(
    name: String, private val get: (RobotVariable) -> String, private val set: (RobotVariable, String) -> Unit
) : ColumnInfo<RobotVariable, String>(name) {
    override fun valueOf(item: RobotVariable): String = get(item)
    override fun isCellEditable(item: RobotVariable): Boolean = true
    override fun setValue(item: RobotVariable, value: String) = set(item, value)
}

private fun modeText(mode: RobotRunMode): String = when (mode) {
    RobotRunMode.INHERIT -> RobotCodeBundle.message("run.options.mode.inherit")
    RobotRunMode.RPA -> RobotCodeBundle.message("run.options.mode.rpa")
    RobotRunMode.NORPA -> RobotCodeBundle.message("run.options.mode.norpa")
}

private fun profilesKindText(kind: RobotRunProfilesKind): String = when (kind) {
    RobotRunProfilesKind.PROJECT -> RobotCodeBundle.message("run.options.profiles.project")
    RobotRunProfilesKind.DEFAULTS -> RobotCodeBundle.message("run.options.profiles.defaults")
    RobotRunProfilesKind.CUSTOM -> RobotCodeBundle.message("run.options.profiles.custom")
}

/**
 * An optional field of the [group] of "Modify options", by default "Robot Framework": a row with [label], the [content]
 * and the [comment], shown again when the editor opens while [isSet] holds for the stored options.
 */
private fun optionFragment(
    id: String,
    name: String,
    label: String,
    comment: String,
    isSet: (RobotCodeRunConfigurationOptions) -> Boolean,
    reset: (RobotCodeRunConfigurationOptions) -> Unit,
    apply: (RobotCodeRunConfigurationOptions) -> Unit,
    group: String = RobotCodeBundle.message("run.target.group"),
    content: Row.() -> Unit
): RobotFragment {
    val component = panel {
        row(label) { content() }.rowComment(comment)
    }
    return SettingsEditorFragment<RobotCodeRunConfiguration, JComponent>(
        id, name, group, component,
        { configuration, _ -> reset(configuration.options) },
        { configuration, _ -> apply(configuration.options) },
        { isSet(it.options) }
    )
}

/**
 * The fragments for the Robot Framework options of a run configuration: "Robot arguments", always shown, and the
 * optional fields of the "Robot Framework" group of "Modify options". Chosen files and folders are added relative to
 * the [workingDirectory].
 */
internal fun robotOptionFragments(
    project: Project, hasModule: () -> Boolean, workingDirectory: () -> Path?
): List<RobotFragment> {
    // a list of entries in the field of the target's lists: separated by spaces, quoted when they contain spaces; a
    // list of paths has macros and a button that adds what the [chooser] picks
    fun listFragment(
        id: String, name: String, label: String, comment: String,
        property: KMutableProperty1<RobotCodeRunConfigurationOptions, MutableList<String>>,
        chooser: (() -> FileChooserDescriptor)? = null, chooserText: String = ""
    ): RobotFragment {
        val field = RawCommandLineEditor()
        if (chooser != null) {
            addMacros(field.editorField, MacrosDialog.Filters.ANY_PATH, hasModule)
        }
        return optionFragment(
            id, name, label, comment,
            { property.get(it).isNotEmpty() },
            { field.text = joinTargetEntries(property.get(it)) },
            { property.set(it, parseTargetEntries(field.text).toMutableList()) }
        ) {
            cell(field).align(AlignX.FILL).resizableColumn()
            if (chooser != null) {
                button(chooserText) {
                    val files = FileChooser.chooseFiles(chooser(), project, null)
                    val chosen = files.map { pathRelativeTo(it.toNioPath(), workingDirectory()) }
                    field.text = joinTargetEntries(parseTargetEntries(field.text) + chosen)
                }
            }
        }
    }

    val robotArgumentsField = RawCommandLineEditor().apply {
        editorField.emptyText.text = RobotCodeBundle.message("run.robotArguments.placeholder")
        addMacros(editorField, MacrosDialog.Filters.ALL, hasModule)
    }
    val robotArguments = SettingsEditorFragment<RobotCodeRunConfiguration, JComponent>(
        "robotcode.robotArguments", RobotCodeBundle.message("run.robotArguments.name"),
        RobotCodeBundle.message("run.target.group"),
        panel {
            row(RobotCodeBundle.message("run.robotArguments.label")) { cell(robotArgumentsField).align(AlignX.FILL) }
        },
        { configuration, _ -> robotArgumentsField.text = configuration.options.robotArguments ?: "" },
        { configuration, _ -> configuration.options.robotArguments = robotArgumentsField.text },
        { true }
    )
    robotArguments.isRemovable = false

    // a plain table keeps the order of the rows; the platform's table for environment variables sorts them by name
    val variablesModel = ListTableModel<RobotVariable>(
        VariableColumn(
            RobotCodeBundle.message("run.options.variables.column.name"), { it.name }, { v, s -> v.name = s }
        ),
        VariableColumn(
            RobotCodeBundle.message("run.options.variables.column.value"), { it.value }, { v, s -> v.value = s }
        )
    )
    val variablesTable = TableView(variablesModel)
    val variablesPanel = ToolbarDecorator.createDecorator(variablesTable, object : ElementProducer<RobotVariable> {
        override fun createElement() = RobotVariable("", "")
        override fun canCreateElement() = true
    }).createPanel()
    val variables = optionFragment(
        "robotcode.variables", RobotCodeBundle.message("run.options.variables.name"),
        RobotCodeBundle.message("run.options.variables.label"),
        RobotCodeBundle.message("run.options.variables.comment"),
        { it.variables.isNotEmpty() },
        { options -> variablesModel.items = options.variables.map { RobotVariable(it.key, it.value) }.toMutableList() },
        { options ->
            TableUtil.stopEditing(variablesTable)
            // rows without a name are dropped
            options.variables = variablesModel.items.filter { it.name.isNotBlank() }
                .associateTo(linkedMapOf()) { it.name.trim() to it.value }
        }
    ) { cell(variablesPanel).align(AlignX.FILL) }

    val outputDirField = ExtendableTextField()
    addMacros(outputDirField, MacrosDialog.Filters.DIRECTORY_PATH, hasModule)
    val outputDirChooser = TextFieldWithBrowseButton(outputDirField) {
        val base = workingDirectory()
        val files = LocalFileSystem.getInstance()
        val start = chooserStart(outputDirField.text, base)?.let { files.findFileByNioFile(it) }
            ?: base?.let { files.findFileByNioFile(it) }
        FileChooser.chooseFile(FileChooserDescriptorFactory.singleDir(), project, start)?.let {
            outputDirField.text = pathRelativeTo(it.toNioPath(), base)
        }
    }
    val outputDir = optionFragment(
        "robotcode.outputDir", RobotCodeBundle.message("run.options.outputDir.name"),
        RobotCodeBundle.message("run.options.outputDir.label"),
        RobotCodeBundle.message("run.options.outputDir.comment"),
        { !it.outputDir.isNullOrBlank() },
        { outputDirField.text = it.outputDir ?: "" },
        { it.outputDir = outputDirField.text.trim() }
    ) { cell(outputDirChooser).align(AlignX.FILL) }

    val modeBox = ComboBox(RobotRunMode.entries.toTypedArray())
    modeBox.renderer = textListCellRenderer<RobotRunMode?> { it?.let(::modeText) }
    val mode = optionFragment(
        "robotcode.mode", RobotCodeBundle.message("run.options.mode.name"),
        RobotCodeBundle.message("run.options.mode.label"), RobotCodeBundle.message("run.options.mode.comment"),
        { it.mode != RobotRunMode.INHERIT },
        { modeBox.selectedItem = it.mode },
        { it.mode = modeBox.selectedItem as? RobotRunMode ?: RobotRunMode.INHERIT }
    ) { cell(modeBox) }

    val dryRun = SettingsEditorFragment.createTag<RobotCodeRunConfiguration>(
        "robotcode.dryRun", RobotCodeBundle.message("run.options.dryRun.name"),
        RobotCodeBundle.message("run.target.group"),
        { it.options.dryRun },
        { configuration, value -> configuration.options.dryRun = value }
    )

    // the warning about profiles that robot.toml no longer defines checks against the cached list
    fun readProfileList() {
        if (!project.isDefault) {
            project.profileListCache.readInBackground()
        }
    }

    val profilesBox = ComboBox(RobotRunProfilesKind.entries.toTypedArray())
    profilesBox.renderer = textListCellRenderer<RobotRunProfilesKind?> { it?.let(::profilesKindText) }
    profilesBox.addItemListener { event ->
        if (event.stateChange == ItemEvent.SELECTED && event.item == RobotRunProfilesKind.CUSTOM) {
            readProfileList()
        }
    }
    // the names of "Custom" as the other lists; "Select..." opens the profile list of the General page with them
    val profilesField = RawCommandLineEditor()
    val profiles = optionFragment(
        "robotcode.profiles", RobotCodeBundle.message("run.options.profiles.name"),
        RobotCodeBundle.message("run.options.profiles.label"), RobotCodeBundle.message("run.options.profiles.comment"),
        { it.profilesKind != RobotRunProfilesKind.PROJECT },
        { options ->
            profilesBox.selectedItem = options.profilesKind
            profilesField.text = joinTargetEntries(options.profiles)
            if (options.profilesKind == RobotRunProfilesKind.CUSTOM) {
                readProfileList()
            }
        },
        { options ->
            val kind = profilesBox.selectedItem as? RobotRunProfilesKind ?: RobotRunProfilesKind.PROJECT
            options.profilesKind = kind
            options.profiles = if (kind == RobotRunProfilesKind.CUSTOM) {
                parseTargetEntries(profilesField.text).toMutableList()
            } else {
                mutableListOf()
            }
        }
    ) {
        val custom = profilesBox.selectedValueIs(RobotRunProfilesKind.CUSTOM)
        cell(profilesBox)
        cell(profilesField).align(AlignX.FILL).resizableColumn().visibleIf(custom)
        // settings for new projects have no robot.toml to read profiles from
        if (!project.isDefault) {
            button(RobotCodeBundle.message("run.options.profiles.select")) {
                project.chooseProfiles(parseTargetEntries(profilesField.text)) { cleaned ->
                    profilesField.text = joinTargetEntries(cleaned)
                }?.let { profilesField.text = joinTargetEntries(it) }
            }.visibleIf(custom)
        }
    }

    return listOf(
        robotArguments,
        variables,
        listFragment(
            "robotcode.variableFiles", RobotCodeBundle.message("run.options.variableFiles.name"),
            RobotCodeBundle.message("run.options.variableFiles.label"),
            RobotCodeBundle.message("run.options.variableFiles.comment"),
            RobotCodeRunConfigurationOptions::variableFiles,
            { FileChooserDescriptorFactory.multiFiles() }, RobotCodeBundle.message("run.options.variableFiles.add")
        ),
        listFragment(
            "robotcode.pythonPath", RobotCodeBundle.message("run.options.pythonPath.name"),
            RobotCodeBundle.message("run.options.pythonPath.label"),
            RobotCodeBundle.message("run.options.pythonPath.comment"),
            RobotCodeRunConfigurationOptions::pythonPath,
            { FileChooserDescriptorFactory.multiFilesOrDirs() }, RobotCodeBundle.message("run.target.paths.browse")
        ),
        listFragment(
            "robotcode.languages", RobotCodeBundle.message("run.options.languages.name"),
            RobotCodeBundle.message("run.options.languages.label"),
            RobotCodeBundle.message("run.options.languages.comment"),
            RobotCodeRunConfigurationOptions::languages
        ),
        listFragment(
            "robotcode.includeTags", RobotCodeBundle.message("run.options.includeTags.name"),
            RobotCodeBundle.message("run.options.includeTags.label"),
            RobotCodeBundle.message("run.options.includeTags.comment"),
            RobotCodeRunConfigurationOptions::includeTags
        ),
        listFragment(
            "robotcode.excludeTags", RobotCodeBundle.message("run.options.excludeTags.name"),
            RobotCodeBundle.message("run.options.excludeTags.label"),
            RobotCodeBundle.message("run.options.excludeTags.comment"),
            RobotCodeRunConfigurationOptions::excludeTags
        ),
        outputDir,
        mode,
        dryRun,
        profiles,
    )
}

private fun projectDefaultText(): String = RobotCodeBundle.message("run.debug.projectDefault")

private fun wrapperText(wrapper: RobotRunWrapper): String = when (wrapper) {
    RobotRunWrapper.INHERIT -> projectDefaultText()
    RobotRunWrapper.PROFILE -> RobotCodeBundle.message("run.debug.wrapper.profile")
    RobotRunWrapper.CUSTOM -> RobotCodeBundle.message("run.debug.wrapper.custom")
    RobotRunWrapper.NONE -> RobotCodeBundle.message("run.debug.wrapper.none")
}

private fun switchText(switch: RobotRunSwitch): String = when (switch) {
    RobotRunSwitch.INHERIT -> projectDefaultText()
    RobotRunSwitch.ON -> RobotCodeBundle.message("run.debug.switch.on")
    RobotRunSwitch.OFF -> RobotCodeBundle.message("run.debug.switch.off")
}

private fun openOutputText(choice: RobotRunOpenOutput): String = when (choice) {
    RobotRunOpenOutput.INHERIT -> projectDefaultText()
    RobotRunOpenOutput.NONE -> openOutputLabel(RobotOpenOutput.NONE)
    RobotRunOpenOutput.REPORT -> openOutputLabel(RobotOpenOutput.REPORT)
    RobotRunOpenOutput.LOG -> openOutputLabel(RobotOpenOutput.LOG)
}

/** A connection timeout as typed: 0 for an empty field, whole seconds above 0, or null for anything else. */
internal fun parseConnectionTimeout(text: String): Int? {
    val trimmed = text.trim()
    if (trimmed.isEmpty()) return 0
    return trimmed.toIntOrNull()?.takeIf { it > 0 }
}

/**
 * The fragments of the "Run & Debug" group of "Modify options": the values that the "Run" and "Debug" settings pages
 * provide as project defaults, with the labels of these pages, and the options that only a configuration has.
 */
internal fun runDebugFragments(): List<RobotFragment> {
    val group = RobotCodeBundle.message("run.debug.group")

    // a command line as the robot arguments, passed as typed
    fun commandLineFragment(
        id: String, key: String, property: KMutableProperty1<RobotCodeRunConfigurationOptions, String?>
    ): RobotFragment {
        val field = RawCommandLineEditor()
        return optionFragment(
            id, RobotCodeBundle.message("$key.name"), RobotCodeBundle.message("$key.label"),
            RobotCodeBundle.message("$key.comment"),
            { !property.get(it).isNullOrBlank() },
            { field.text = property.get(it).orEmpty() },
            { property.set(it, field.text) },
            group
        ) { cell(field).align(AlignX.FILL) }
    }

    fun switchFragment(
        id: String, key: String, property: KMutableProperty1<RobotCodeRunConfigurationOptions, RobotRunSwitch>
    ): RobotFragment {
        val box = ComboBox(RobotRunSwitch.entries.toTypedArray())
        box.renderer = textListCellRenderer<RobotRunSwitch?> { it?.let(::switchText) }
        return optionFragment(
            id, RobotCodeBundle.message("$key.name"), RobotCodeBundle.message("$key.label"),
            RobotCodeBundle.message("run.debug.output.comment"),
            { property.get(it) != RobotRunSwitch.INHERIT },
            { box.selectedItem = property.get(it) },
            { property.set(it, box.selectedItem as? RobotRunSwitch ?: RobotRunSwitch.INHERIT) },
            group
        ) { cell(box) }
    }

    val wrapperBox = ComboBox(RobotRunWrapper.entries.toTypedArray())
    wrapperBox.renderer = textListCellRenderer<RobotRunWrapper?> { it?.let(::wrapperText) }
    val wrapperField = RawCommandLineEditor()
    val wrapper = optionFragment(
        "robotcode.wrapper", RobotCodeBundle.message("run.debug.wrapper.name"),
        RobotCodeBundle.message("run.debug.wrapper.label"), RobotCodeBundle.message("run.debug.wrapper.comment"),
        { it.wrapper != RobotRunWrapper.INHERIT },
        { options ->
            wrapperBox.selectedItem = options.wrapper
            wrapperField.text = options.wrapperCommand.orEmpty()
        },
        { options ->
            val choice = wrapperBox.selectedItem as? RobotRunWrapper ?: RobotRunWrapper.INHERIT
            options.wrapper = choice
            options.wrapperCommand = if (choice == RobotRunWrapper.CUSTOM) wrapperField.text else null
        },
        group
    ) {
        cell(wrapperBox)
        cell(wrapperField).align(AlignX.FILL).resizableColumn()
            .visibleIf(wrapperBox.selectedValueIs(RobotRunWrapper.CUSTOM))
    }

    val openOutputBox = ComboBox(RobotRunOpenOutput.entries.toTypedArray())
    openOutputBox.renderer = textListCellRenderer<RobotRunOpenOutput?> { it?.let(::openOutputText) }
    val openOutput = optionFragment(
        "robotcode.openOutputAfterRun", RobotCodeBundle.message("run.debug.openOutputAfterRun.name"),
        RobotCodeBundle.message("run.debug.openOutputAfterRun.label"),
        RobotCodeBundle.message("run.debug.openOutputAfterRun.comment"),
        { it.openOutputAfterRun != RobotRunOpenOutput.INHERIT },
        { openOutputBox.selectedItem = it.openOutputAfterRun },
        { it.openOutputAfterRun = openOutputBox.selectedItem as? RobotRunOpenOutput ?: RobotRunOpenOutput.INHERIT },
        group
    ) { cell(openOutputBox) }

    val stopOnEntry = SettingsEditorFragment.createTag<RobotCodeRunConfiguration>(
        "robotcode.stopOnEntry", RobotCodeBundle.message("run.debug.stopOnEntry.name"), group,
        { it.options.stopOnEntry },
        { configuration, value -> configuration.options.stopOnEntry = value }
    )

    val timeoutField = JBTextField(6).apply { emptyText.text = DEBUGGER_CONNECT_TIMEOUT_SECONDS.toString() }
    val connectionTimeout = optionFragment(
        "robotcode.connectionTimeout", RobotCodeBundle.message("run.debug.connectionTimeout.name"),
        RobotCodeBundle.message("run.debug.connectionTimeout.label"),
        RobotCodeBundle.message("run.debug.connectionTimeout.comment"),
        { it.connectionTimeout > 0 },
        { timeoutField.text = it.connectionTimeout.takeIf { seconds -> seconds > 0 }?.toString().orEmpty() },
        { it.connectionTimeout = parseConnectionTimeout(timeoutField.text) ?: 0 },
        group
    ) { cell(timeoutField) }
    connectionTimeout.setValidation {
        listOfNotNull(
            if (parseConnectionTimeout(timeoutField.text) == null) {
                ValidationInfo(RobotCodeBundle.message("run.debug.connectionTimeout.invalid"), timeoutField)
            } else {
                null
            }
        )
    }

    return listOf(
        wrapper,
        commandLineFragment(
            "robotcode.robotCodeArguments", "run.debug.robotCodeArguments",
            RobotCodeRunConfigurationOptions::robotCodeArguments
        ),
        switchFragment(
            "robotcode.outputMessages", "run.debug.outputMessages", RobotCodeRunConfigurationOptions::outputMessages
        ),
        switchFragment("robotcode.outputLog", "run.debug.outputLog", RobotCodeRunConfigurationOptions::outputLog),
        switchFragment(
            "robotcode.outputTimestamps", "run.debug.outputTimestamps",
            RobotCodeRunConfigurationOptions::outputTimestamps
        ),
        switchFragment(
            "robotcode.attachPython", "run.debug.attachPython", RobotCodeRunConfigurationOptions::attachPython
        ),
        openOutput,
        stopOnEntry,
        connectionTimeout,
        commandLineFragment(
            "robotcode.debuggerArguments", "run.debug.debuggerArguments",
            RobotCodeRunConfigurationOptions::debuggerArguments
        )
    )
}
