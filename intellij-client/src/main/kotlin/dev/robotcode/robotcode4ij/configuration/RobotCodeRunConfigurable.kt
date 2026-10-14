package dev.robotcode.robotcode4ij.configuration

import com.intellij.ide.browsers.WebBrowser
import com.intellij.ide.browsers.WebBrowserManager
import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.bindItem
import com.intellij.ui.dsl.builder.panel
import com.intellij.ui.dsl.listCellRenderer.textListCellRenderer
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.execution.RobotOpenOutput
import dev.robotcode.robotcode4ij.execution.RobotOpenOutputTarget

/**
 * The "Run" page below the "Robot Framework" node: the settings of VS Code's settings category "Run" that the runs of
 * Robot Framework run configurations use unless a configuration sets its own. Runs read them when they start, so
 * applying them restarts nothing.
 */
class RobotCodeRunConfigurable(project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.run.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.run"
) {

    private val settings = RobotCodeProjectConfiguration.getInstance(project)

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        // the entries of the "Open In | Browser" menu of HTML files
        val targets = listOf(
            OutputTargetChoice(RobotOpenOutputTarget.BUILT_IN_PREVIEW),
            OutputTargetChoice(RobotOpenOutputTarget.DEFAULT_BROWSER)
        ) + WebBrowserManager.getInstance().activeBrowsers.map { OutputTargetChoice(RobotOpenOutputTarget.BROWSER, it) }

        return panel {
            row(RobotCodeBundle.message("settings.run.openOutputAfterRun")) {
                comboBox(RobotOpenOutput.entries, textListCellRenderer<RobotOpenOutput?> { it?.let(::openOutputLabel) })
                    .bindItem(
                        { settings.runOpenOutputAfterRun },
                        { settings.runOpenOutputAfterRun = it ?: RobotOpenOutput.NONE }
                    )
            }.rowComment(RobotCodeBundle.message("settings.run.openOutputAfterRun.comment"))
            row(RobotCodeBundle.message("settings.run.openOutputTarget")) {
                comboBox(targets, textListCellRenderer<OutputTargetChoice?> { it?.label })
                    .bindItem(
                        { storedTarget(targets) },
                        {
                            settings.runOpenOutputTarget = it?.target ?: RobotOpenOutputTarget.BUILT_IN_PREVIEW
                            settings.runOpenOutputBrowser = it?.browser?.id?.toString() ?: ""
                        }
                    )
            }.rowComment(RobotCodeBundle.message("settings.run.openOutputTarget.comment"))
            row {
                comment(RobotCodeBundle.message("settings.runDefaults.comment"))
            }
        }
    }

    // a stored browser that is no longer active shows as the default browser, which runs then take
    private fun storedTarget(targets: List<OutputTargetChoice>): OutputTargetChoice {
        val target = settings.runOpenOutputTarget
        return targets.firstOrNull {
            it.target == target && (target != RobotOpenOutputTarget.BROWSER ||
                it.browser?.id?.toString() == settings.runOpenOutputBrowser)
        } ?: targets.first { it.target == RobotOpenOutputTarget.DEFAULT_BROWSER }
    }
}

/** An entry of "Open output target": the built-in preview, the default browser, or one of the active [browser]s. */
private class OutputTargetChoice(val target: RobotOpenOutputTarget, val browser: WebBrowser? = null) {
    val label: String
        get() = when (target) {
            RobotOpenOutputTarget.BUILT_IN_PREVIEW -> RobotCodeBundle.message("settings.run.openOutputTarget.preview")
            RobotOpenOutputTarget.DEFAULT_BROWSER -> RobotCodeBundle.message("settings.run.openOutputTarget.default")
            RobotOpenOutputTarget.BROWSER -> browser?.name ?: ""
        }
}

/** The text for [output] in the choices of "Open output after run". */
internal fun openOutputLabel(output: RobotOpenOutput): String {
    return when (output) {
        RobotOpenOutput.NONE -> RobotCodeBundle.message("settings.run.openOutputAfterRun.none")
        RobotOpenOutput.REPORT -> RobotCodeBundle.message("settings.run.openOutputAfterRun.report")
        RobotOpenOutput.LOG -> RobotCodeBundle.message("settings.run.openOutputAfterRun.log")
    }
}
