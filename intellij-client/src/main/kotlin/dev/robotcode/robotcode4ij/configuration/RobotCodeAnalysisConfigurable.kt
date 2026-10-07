package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.BoundSearchableConfigurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogPanel
import com.intellij.openapi.ui.ValidationInfo
import com.intellij.ui.dsl.builder.bindItem
import com.intellij.ui.dsl.builder.bindSelected
import com.intellij.ui.dsl.builder.bindText
import com.intellij.ui.dsl.builder.columns
import com.intellij.ui.dsl.builder.panel
import com.intellij.ui.dsl.listCellRenderer.textListCellRenderer
import com.intellij.ui.layout.ValidationInfoBuilder
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettings.CacheSaveLocation
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettings.DiagnosticMode
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettings.ProgressMode
import dev.robotcode.robotcode4ij.restartAll

/**
 * The "Analysis" page below the "Robot Framework" node: the settings of VS Code's settings category "Analysis", and
 * those of the categories "Workspace" and "Experimental", which have one setting each.
 */
class RobotCodeAnalysisConfigurable(private val project: Project) : BoundSearchableConfigurable(
    RobotCodeBundle.message("settings.analysis.displayName"),
    helpTopic = "",
    "dev.robotcode.robotcode4ij.projectsettings.analysis"
) {

    private val settings = RobotCodeProjectConfiguration.getInstance(project)

    private lateinit var dialogPanel: DialogPanel

    // RobotCode has no topic in the IDE help, so the settings dialog falls back to the parent's topic
    override fun getHelpTopic(): String? = null

    override fun createPanel(): DialogPanel {
        dialogPanel = panel {
            row(RobotCodeBundle.message("settings.analysis.diagnosticMode")) {
                comboBox(DiagnosticMode.entries, textListCellRenderer<DiagnosticMode?> { it?.let(::label) })
                    .bindItem(
                        { choiceOf<DiagnosticMode>(settings.analysisDiagnosticMode) },
                        { settings.analysisDiagnosticMode = (it ?: DiagnosticMode.OPEN_FILES_ONLY).value }
                    )
            }.rowComment(RobotCodeBundle.message("settings.analysis.diagnosticMode.comment"))
            row(RobotCodeBundle.message("settings.analysis.progressMode")) {
                comboBox(ProgressMode.entries, textListCellRenderer<ProgressMode?> { it?.let(::label) })
                    .bindItem(
                        { choiceOf<ProgressMode>(settings.analysisProgressMode) },
                        { settings.analysisProgressMode = (it ?: ProgressMode.OFF).value }
                    )
            }.rowComment(RobotCodeBundle.message("settings.analysis.progressMode.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.analysis.findUnusedReferences"))
                    .bindSelected(settings::analysisFindUnusedReferences)
            }.rowComment(RobotCodeBundle.message("settings.analysis.findUnusedReferences.comment"))
            row {
                checkBox(RobotCodeBundle.message("settings.analysis.referencesCodeLens"))
                    .bindSelected(settings::analysisReferencesCodeLens)
            }.rowComment(RobotCodeBundle.message("settings.analysis.referencesCodeLens.comment"))
            group(RobotCodeBundle.message("settings.analysis.cache")) {
                row(RobotCodeBundle.message("settings.analysis.cache.saveLocation")) {
                    comboBox(CacheSaveLocation.entries, textListCellRenderer<CacheSaveLocation?> { it?.let(::label) })
                        .bindItem(
                            { choiceOf<CacheSaveLocation>(settings.analysisCacheSaveLocation) },
                            { settings.analysisCacheSaveLocation = (it ?: CacheSaveLocation.WORKSPACE_STORAGE).value }
                        )
                }.rowComment(RobotCodeBundle.message("settings.analysis.cache.saveLocation.comment"))
                row(RobotCodeBundle.message("settings.analysis.cache.ignoredLibraries")) {
                    listField(settings::analysisCacheIgnoredLibraries)
                }.rowComment(RobotCodeBundle.message("settings.analysis.cache.ignoredLibraries.comment"))
                row(RobotCodeBundle.message("settings.analysis.cache.ignoredVariables")) {
                    listField(settings::analysisCacheIgnoredVariables)
                }.rowComment(RobotCodeBundle.message("settings.analysis.cache.ignoredVariables.comment"))
                row(RobotCodeBundle.message("settings.analysis.cache.ignoreArgumentsForLibrary")) {
                    listField(settings::analysisCacheIgnoreArgumentsForLibrary)
                }.rowComment(RobotCodeBundle.message("settings.analysis.cache.ignoreArgumentsForLibrary.comment"))
                row {
                    comment(RobotCodeBundle.message("settings.analysis.cache.comment"))
                }
            }
            group(RobotCodeBundle.message("settings.analysis.robot")) {
                row(RobotCodeBundle.message("settings.analysis.robot.globalLibrarySearchOrder")) {
                    listField(settings::analysisRobotGlobalLibrarySearchOrder)
                }.rowComment(RobotCodeBundle.message("settings.analysis.robot.globalLibrarySearchOrder.comment"))
                row(RobotCodeBundle.message("settings.analysis.robot.loadLibraryTimeout")) {
                    textField()
                        .columns(6)
                        .bindText(
                            { settings.analysisRobotLoadLibraryTimeout.takeIf { it > 0 }?.toString() ?: "" },
                            { text ->
                                parseLoadLibraryTimeout(text)?.let { settings.analysisRobotLoadLibraryTimeout = it }
                            }
                        )
                        .validationOnInput { checkLoadLibraryTimeout(it.text) }
                        .validationOnApply { checkLoadLibraryTimeout(it.text) }
                    label(RobotCodeBundle.message("settings.analysis.robot.loadLibraryTimeout.seconds"))
                }.rowComment(RobotCodeBundle.message("settings.analysis.robot.loadLibraryTimeout.comment"))
            }
            group(RobotCodeBundle.message("settings.analysis.diagnosticModifiers")) {
                row {
                    comment(RobotCodeBundle.message("settings.analysis.diagnosticModifiers.comment"))
                }
                row(RobotCodeBundle.message("settings.analysis.diagnosticModifiers.ignore")) {
                    listField(settings::analysisDiagnosticModifiersIgnore)
                }
                row(RobotCodeBundle.message("settings.analysis.diagnosticModifiers.error")) {
                    listField(settings::analysisDiagnosticModifiersError)
                }
                row(RobotCodeBundle.message("settings.analysis.diagnosticModifiers.warning")) {
                    listField(settings::analysisDiagnosticModifiersWarning)
                }
                row(RobotCodeBundle.message("settings.analysis.diagnosticModifiers.information")) {
                    listField(settings::analysisDiagnosticModifiersInformation)
                }.rowComment(RobotCodeBundle.message("settings.analysis.diagnosticModifiers.information.comment"))
                row(RobotCodeBundle.message("settings.analysis.diagnosticModifiers.hint")) {
                    listField(settings::analysisDiagnosticModifiersHint)
                }.rowComment(RobotCodeBundle.message("settings.analysis.diagnosticModifiers.hint.comment"))
            }
            group(RobotCodeBundle.message("settings.analysis.workspace")) {
                row(RobotCodeBundle.message("settings.analysis.workspace.excludePatterns")) {
                    listField(settings::workspaceExcludePatterns)
                }.rowComment(RobotCodeBundle.message("settings.analysis.workspace.excludePatterns.comment"))
            }
            group(RobotCodeBundle.message("settings.analysis.experimental")) {
                row {
                    checkBox(RobotCodeBundle.message("settings.analysis.experimental.semanticModel"))
                        .bindSelected(settings::experimentalSemanticModel)
                }.rowComment(RobotCodeBundle.message("settings.analysis.experimental.semanticModel.comment"))
            }
        }
        return dialogPanel
    }

    override fun apply() {
        dialogPanel.checkValues()
        super.apply()
        // shows the stored values as the fields write them, for example the list entries
        reset()
        project.restartAll()
    }

    private fun ValidationInfoBuilder.checkLoadLibraryTimeout(text: String): ValidationInfo? {
        return if (parseLoadLibraryTimeout(text) == null) {
            error(RobotCodeBundle.message("settings.analysis.robot.loadLibraryTimeout.invalid"))
        } else {
            null
        }
    }

    private fun label(mode: DiagnosticMode): String {
        return when (mode) {
            DiagnosticMode.OPEN_FILES_ONLY -> RobotCodeBundle.message("settings.analysis.diagnosticMode.openFilesOnly")
            DiagnosticMode.WORKSPACE -> RobotCodeBundle.message("settings.analysis.diagnosticMode.workspace")
        }
    }

    private fun label(mode: ProgressMode): String {
        return when (mode) {
            ProgressMode.OFF -> RobotCodeBundle.message("settings.analysis.progressMode.off")
            ProgressMode.SIMPLE -> RobotCodeBundle.message("settings.analysis.progressMode.simple")
            ProgressMode.DETAILED -> RobotCodeBundle.message("settings.analysis.progressMode.detailed")
        }
    }

    private fun label(location: CacheSaveLocation): String {
        return when (location) {
            CacheSaveLocation.WORKSPACE_STORAGE ->
                RobotCodeBundle.message("settings.analysis.cache.saveLocation.workspaceStorage")

            CacheSaveLocation.WORKSPACE_FOLDER ->
                RobotCodeBundle.message("settings.analysis.cache.saveLocation.workspaceFolder")
        }
    }
}

/**
 * The stored load library timeout for the text of its field: 0 for an empty field, which means no timeout is set, or
 * null for a text that is not a whole number from 1 to 3600.
 */
internal fun parseLoadLibraryTimeout(text: String): Int? {
    val trimmed = text.trim()
    if (trimmed.isEmpty()) {
        return 0
    }
    return trimmed.toIntOrNull()?.takeIf { it in 1..3600 }
}
