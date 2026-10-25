package dev.robotcode.robotcode4ij.configuration

import com.intellij.execution.CantRunException
import com.intellij.execution.ExecutionException
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.CapturingProcessAdapter
import com.intellij.execution.process.OSProcessHandler
import com.intellij.execution.process.ProcessOutput
import com.intellij.openapi.project.Project
import com.intellij.platform.ide.progress.runWithModalProgressBlocking
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import dev.robotcode.robotcode4ij.defaultPathArguments
import dev.robotcode.robotcode4ij.editor.updateRobotCodeStatusBar
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import dev.robotcode.robotcode4ij.robotSettings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** A profile as `robotcode profiles list` reports it. */
@Serializable
internal data class ProfileInfo(val name: String, val description: String = "", val selected: Boolean = false)

/**
 * The output of `robotcode --format json profiles list`. The messages explain an empty list; [unknownSelected] names the
 * names and patterns of the selection that select no profile.
 */
@Serializable
internal data class ProfileList(
    val profiles: List<ProfileInfo> = emptyList(),
    val messages: List<String> = emptyList(),
    val unknownSelected: List<String> = emptyList()
)

private val profileListJson = Json { ignoreUnknownKeys = true }

/**
 * What the profile list shows for a selection, as VS Code's picker does. [selection] is the selection without the
 * [removed] names, which `robot.toml` no longer defines.
 */
internal data class ProfileChoice(
    val profiles: List<ProfileInfo>,
    val messages: List<String>,
    val removed: List<String>,
    val selection: List<String>
) {
    /** The profiles that `robotcode` reports as selected, which are those of `default-profiles` without a selection. */
    val checked: List<String>
        get() = profiles.filter { it.selected }.map { it.name }

    /** The selection that confirming stores, in the order of the list; no name means that `default-profiles` apply. */
    fun confirm(checkedNames: Collection<String>): List<String> {
        return profiles.map { it.name }.filter { it in checkedNames }
    }
}

/**
 * The choice for [selection] and the [list] that `robotcode` read for it. Only the names that the list reports as
 * selecting no profile leave the selection: patterns and hidden profiles that select a profile stay, and a list that
 * could not be read removes nothing.
 */
internal fun profileChoice(selection: List<String>, list: ProfileList): ProfileChoice {
    val removed = selection.filter { it in list.unknownSelected }
    return ProfileChoice(list.profiles, list.messages, removed, selection.filter { it !in removed })
}

/** The profile list, or the text that says why it could not be read. */
internal sealed class ProfileListResult {
    data class Read(val list: ProfileList) : ProfileListResult()
    data class Error(val message: String) : ProfileListResult()
}

private const val ERROR_LINES = 5

/** The profile list in the [output] of `robotcode profiles list`, or the beginning of its error output. */
internal fun profileListResult(output: ProcessOutput): ProfileListResult {
    if (output.exitCode != 0) {
        val lines = output.stderr.lines().filter { it.isNotBlank() }.take(ERROR_LINES)
        val details = lines.joinToString("\n")
            .ifEmpty { RobotCodeBundle.message("profiles.error.exitCode", output.exitCode.toString()) }
        return ProfileListResult.Error(RobotCodeBundle.message("profiles.error", details))
    }
    return try {
        ProfileListResult.Read(profileListJson.decodeFromString<ProfileList>(output.stdout))
    } catch (_: IllegalArgumentException) {
        ProfileListResult.Error(
            RobotCodeBundle.message("profiles.error", RobotCodeBundle.message("profiles.error.output"))
        )
    }
}

/**
 * Reads the profile list for [selection] with a progress that can be cancelled, once the project's interpreter is
 * usable. Returns null when the user cancels the progress.
 */
internal fun Project.readProfileList(selection: List<String>): ProfileListResult? {
    return try {
        robotCodeEnvironment.ensureUsableForRun()
        val commandLine = profileListCommandLine(selection)
        runWithModalProgressBlocking(this, RobotCodeBundle.message("profiles.progress")) {
            profileListResult(runCancellable(commandLine))
        }
    } catch (e: CantRunException) {
        ProfileListResult.Error(e.message ?: "")
    } catch (_: ExecutionException) {
        ProfileListResult.Error(
            RobotCodeBundle.message("profiles.error", RobotCodeBundle.message("profiles.error.notStarted"))
        )
    } catch (_: CancellationException) {
        null
    }
}

/**
 * Reads the profile list for [selection] without a progress, once the running environment check has finished. Returns
 * null when the project's interpreter is not usable or `robotcode` cannot be started.
 */
internal suspend fun Project.readProfileListInBackground(selection: List<String>): ProfileListResult? {
    val environment = robotCodeEnvironment
    environment.awaitRunningCheck()
    if (!environment.projectState.isUsable) {
        return null
    }
    return try {
        profileListResult(runCancellable(profileListCommandLine(selection)))
    } catch (_: ExecutionException) {
        null
    }
}

// `profiles list` with the default paths of the "Robot" page
private fun Project.profileListCommandLine(selection: List<String>): GeneralCommandLine {
    return buildRobotCodeCommandLine(
        (defaultPathArguments(robotSettings.robotPaths) + listOf("profiles", "list")).toTypedArray(),
        profiles = selection.toTypedArray(), format = "json"
    )
}

private const val POLL_MILLIS = 100L

// ends the process when the progress is cancelled
private suspend fun runCancellable(commandLine: GeneralCommandLine): ProcessOutput = withContext(Dispatchers.IO) {
    val output = ProcessOutput()
    val handler = OSProcessHandler(commandLine)
    handler.addProcessListener(CapturingProcessAdapter(output))
    handler.startNotify()
    try {
        while (!handler.waitFor(POLL_MILLIS)) {
            ensureActive()
        }
    } finally {
        if (!handler.isProcessTerminated) {
            handler.destroyProcess()
        }
    }
    output
}

/**
 * Opens the profile list for [selection]. As soon as the list is read, [cleaned] gets the selection without the
 * profiles that `robot.toml` no longer defines, also when the user then cancels the list. Returns the confirmed
 * selection, or null when the user cancels or the list could not be read.
 */
internal fun Project.chooseProfiles(selection: List<String>, cleaned: (List<String>) -> Unit): List<String>? {
    val result = readProfileList(selection) ?: return null
    val choice = (result as? ProfileListResult.Read)?.let { profileChoice(selection, it.list) }
    if (choice != null && choice.removed.isNotEmpty()) {
        cleaned(choice.selection)
    }
    val dialog = RobotCodeProfilesDialog(this, choice, (result as? ProfileListResult.Error)?.message)
    if (!dialog.showAndGet() || choice == null || choice.profiles.isEmpty()) {
        return null
    }
    return choice.confirm(dialog.checkedNames)
}

/** Stores [profiles] as the project's selection, which restarts the language server and the discovery. */
internal fun Project.storeProfileSelection(profiles: List<String>) {
    val settings = RobotCodePersonalConfiguration.getInstance(this)
    if (profiles != settings.profiles) {
        settings.profiles = profiles.toMutableList()
        publishRobotCodeSettingsChanged()
        updateRobotCodeStatusBar()
    }
}

/** Opens the profile list for the project's selection and stores the selection at once, as VS Code's command does. */
internal fun Project.selectConfigurationProfiles() {
    val selection = RobotCodePersonalConfiguration.getInstance(this).profiles.toList()
    chooseProfiles(selection) { storeProfileSelection(it) }?.let { storeProfileSelection(it) }
}
