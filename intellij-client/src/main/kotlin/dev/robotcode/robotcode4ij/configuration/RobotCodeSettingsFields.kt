package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.fileChooser.FileChooser
import com.intellij.openapi.fileChooser.FileChooserDescriptor
import com.intellij.openapi.options.ConfigurationException
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.RawCommandLineEditor
import com.intellij.ui.TableUtil
import com.intellij.ui.ToolbarDecorator
import com.intellij.ui.components.fields.ExpandableTextField
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.Cell
import com.intellij.ui.dsl.builder.Row
import com.intellij.ui.dsl.builder.bindText
import com.intellij.ui.dsl.builder.toMutableProperty
import com.intellij.ui.table.TableView
import com.intellij.util.ui.ElementProducer
import com.intellij.util.ui.ListTableModel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.execution.RobotVariable
import dev.robotcode.robotcode4ij.execution.VariableColumn
import dev.robotcode.robotcode4ij.execution.pathRelativeTo
import java.nio.file.Path
import javax.swing.JPanel
import kotlin.reflect.KMutableProperty0

/**
 * A text field for a list setting, with the entries separated by semicolons; the expanded field shows one entry per
 * line. Entries are trimmed, and blank entries are left out.
 */
internal fun Row.listField(property: KMutableProperty0<MutableList<String>>): Cell<ExpandableTextField> {
    return expandableTextField({ parseListEntries(it).toMutableList() }, { joinListEntries(it) })
        .align(AlignX.FILL)
        .bindText({ joinListEntries(property.get()) }, { property.set(parseListEntries(it).toMutableList()) })
}

/**
 * A field for a command line, with the arguments separated by spaces and quoted as in IntelliJ's own argument fields.
 * The command line is stored as typed.
 */
internal fun Row.commandLineField(property: KMutableProperty0<String>): Cell<RawCommandLineEditor> {
    return cell(RawCommandLineEditor())
        .align(AlignX.FILL)
        .bind({ it.text }, { editor, text -> editor.text = text }, property.toMutableProperty())
}

/**
 * A [listField] for paths with a button that adds the files or folders that [chooser] picks, relative to the project
 * folder when they lie inside it.
 */
internal fun Row.pathListField(
    property: KMutableProperty0<MutableList<String>>, project: Project, chooser: () -> FileChooserDescriptor,
    buttonText: String
): Cell<ExpandableTextField> {
    val cell = listField(property).resizableColumn()
    button(buttonText) {
        val files = FileChooser.chooseFiles(chooser(), project, null)
        val chosen = files.map { pathRelativeTo(it.toNioPath(), project.basePath?.let { base -> Path.of(base) }) }
        cell.component.text = joinListEntries(parseListEntries(cell.component.text) + chosen)
    }
    return cell
}

/**
 * A table of names and values that keeps the order of its rows, as the run configuration's variables do; rows without a
 * name are dropped.
 */
internal fun Row.nameValueTable(property: KMutableProperty0<MutableMap<String, String>>): Cell<JPanel> {
    val model = ListTableModel<RobotVariable>(
        VariableColumn(
            RobotCodeBundle.message("run.options.variables.column.name"), { it.name }, { v, s -> v.name = s }
        ),
        VariableColumn(
            RobotCodeBundle.message("run.options.variables.column.value"), { it.value }, { v, s -> v.value = s }
        )
    )
    val table = TableView(model)
    val panel = ToolbarDecorator.createDecorator(table, object : ElementProducer<RobotVariable> {
        override fun createElement() = RobotVariable("", "")
        override fun canCreateElement() = true
    }).createPanel()

    fun entries(): LinkedHashMap<String, String> {
        return model.items.filter { it.name.isNotBlank() }.associateTo(linkedMapOf()) { it.name.trim() to it.value }
    }

    return cell(panel).align(AlignX.FILL)
        .onReset { model.items = property.get().map { RobotVariable(it.key, it.value) }.toMutableList() }
        // compared as lists, because maps that differ only in their order are equal
        .onIsModified { entries().toList() != property.get().toList() }
        .onApply {
            TableUtil.stopEditing(table)
            property.set(entries())
        }
}

internal fun parseListEntries(text: String): List<String> {
    return text.split(';').map { it.trim() }.filter { it.isNotEmpty() }
}

internal fun joinListEntries(entries: List<String>): String {
    return entries.map { it.trim() }.filter { it.isNotEmpty() }.joinToString("; ")
}

/**
 * Throws the first validation error of the page. The settings dialog applies a page without running its validations,
 * so an invalid value would be stored otherwise.
 */
internal fun DialogPanel.checkValues() {
    validateAll().firstOrNull()?.let { throw ConfigurationException(it.message) }
}
