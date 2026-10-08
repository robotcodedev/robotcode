package dev.robotcode.robotcode4ij.configuration

import com.intellij.CommonBundle
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogWrapper
import com.intellij.openapi.util.text.StringUtil
import com.intellij.ui.CheckBoxList
import com.intellij.ui.dsl.builder.Align
import com.intellij.ui.dsl.builder.panel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import javax.swing.Action
import javax.swing.JComponent

/**
 * The profile list: the profiles of a [choice] to check, with their descriptions, and one line for the removed
 * profiles, the messages of `robotcode` or the [error] that kept it from reading the list.
 */
internal class RobotCodeProfilesDialog(
    project: Project,
    private val choice: ProfileChoice?,
    private val error: String?
) : DialogWrapper(project) {

    private val profiles = choice?.profiles.orEmpty()

    private val list = object : CheckBoxList<String>() {
        override fun getSecondaryText(index: Int): String? = profiles.getOrNull(index)?.description?.ifBlank { null }
    }

    val checkedNames: List<String>
        get() = list.checkedItems

    init {
        title = RobotCodeBundle.message("profiles.dialog.title")
        val checked = choice?.checked.orEmpty()
        profiles.forEach { list.addItem(it.name, it.name, it.name in checked) }
        if (profiles.isEmpty()) {
            setCancelButtonText(CommonBundle.getCloseButtonText())
        }
        init()
    }

    // nothing to confirm without profiles
    override fun createActions(): Array<Action> {
        return if (profiles.isEmpty()) arrayOf(cancelAction) else super.createActions()
    }

    override fun createCenterPanel(): JComponent {
        val lines = buildList {
            choice?.removed?.takeIf { it.isNotEmpty() }?.let { removed ->
                add(RobotCodeBundle.message("profiles.removed", removed.joinToString(", ") { "\"$it\"" }, removed.size))
            }
            choice?.messages?.let { addAll(it) }
            error?.let { addAll(it.lines()) }
            if (isEmpty() && profiles.isEmpty()) {
                add(RobotCodeBundle.message("profiles.none"))
            }
        }
        return panel {
            if (lines.isNotEmpty()) {
                row {
                    text(lines.joinToString("<br>") { StringUtil.escapeXmlEntities(it) })
                }
            }
            if (profiles.isNotEmpty()) {
                row {
                    scrollCell(list).align(Align.FILL)
                }.resizableRow()
            }
        }
    }

    override fun getPreferredFocusedComponent(): JComponent? = if (profiles.isEmpty()) null else list
}
