package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.ConfigurationException
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.RawCommandLineEditor
import com.intellij.ui.components.fields.ExpandableTextField
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.Cell
import com.intellij.ui.dsl.builder.Row
import com.intellij.ui.dsl.builder.bindText
import com.intellij.ui.dsl.builder.toMutableProperty
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
