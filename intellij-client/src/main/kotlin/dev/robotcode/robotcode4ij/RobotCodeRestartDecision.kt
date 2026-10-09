package dev.robotcode.robotcode4ij

import com.google.gson.JsonObject
import com.intellij.execution.CantRunException
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.openapi.project.Project
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettingsMapper
import dev.robotcode.robotcode4ij.lsp.languageServerCommandLine
import dev.robotcode.robotcode4ij.testing.fullDiscoveryCommandLine

/**
 * What a running language server got at its start. The port is left out, because every start gets another one.
 */
internal data class ServerSnapshot(
    val commandLine: List<String>,
    val environment: Map<String, String>,
    val workDirectory: String?,
    val settings: String,
    val initializationOptions: String
) {
    constructor(commandLine: GeneralCommandLine, settings: JsonObject, initializationOptions: JsonObject) : this(
        commandLine.getCommandLineList(null), commandLine.environment.toMap(), commandLine.workDirectory?.path,
        settings.toString(), initializationOptions.toString()
    )
}

/**
 * What the last full discovery ran with.
 */
internal data class DiscoverySnapshot(
    val commandLine: List<String>,
    val environment: Map<String, String>,
    val workDirectory: String?
) {
    constructor(commandLine: GeneralCommandLine) : this(
        commandLine.getCommandLineList(null), commandLine.environment.toMap(), commandLine.workDirectory?.path
    )
}

/** Whether a change needs a restart of the language server, a full discovery, or both. */
internal data class RestartWork(val server: Boolean, val discovery: Boolean)

/**
 * Compares what the running server and the last discovery got with what they would get now. Without a server or a
 * discovery that ran before, there is nothing to compare, and nothing is needed.
 */
internal fun decideRestart(
    oldServer: ServerSnapshot?,
    newServer: ServerSnapshot?,
    oldDiscovery: DiscoverySnapshot?,
    newDiscovery: DiscoverySnapshot?
): RestartWork {
    return RestartWork(
        server = oldServer != null && newServer != null && oldServer != newServer,
        discovery = oldDiscovery != null && newDiscovery != null && oldDiscovery != newDiscovery
    )
}

private const val PORT_PLACEHOLDER = "<port>"

/** What the language server would get now, or null when its command line cannot be built. */
internal fun Project.serverSnapshot(): ServerSnapshot? {
    return try {
        ServerSnapshot(
            languageServerCommandLine(PORT_PLACEHOLDER),
            RobotCodeServerSettingsMapper.toJsonTree(this),
            RobotCodeServerSettingsMapper.toInitializationOptions(this)
        )
    } catch (_: CantRunException) {
        null
    }
}

/** What a full discovery would run with now, or null when its command line cannot be built. */
internal fun Project.discoverySnapshot(): DiscoverySnapshot? {
    return try {
        DiscoverySnapshot(fullDiscoveryCommandLine())
    } catch (_: CantRunException) {
        null
    }
}
