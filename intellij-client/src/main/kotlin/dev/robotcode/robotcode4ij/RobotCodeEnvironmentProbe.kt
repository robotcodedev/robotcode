package dev.robotcode.robotcode4ij

import com.intellij.execution.process.ProcessOutput
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

internal val MINIMUM_PYTHON = listOf(3, 10)
internal val MINIMUM_ROBOT = listOf(5, 0)

/**
 * Prints one JSON line with the Python version and the Robot Framework version, or the error that importing Robot
 * Framework raised. It imports no RobotCode code and avoids newer syntax, so it also reports the version of an old
 * Python.
 */
internal val PROBE_SNIPPET = """
    import json, sys
    result = {"python": ".".join(str(v) for v in sys.version_info[:3])}
    try:
        from robot.version import VERSION
        result["robot"] = VERSION
    except Exception as e:
        result["robotError"] = "%s: %s" % (type(e).__name__, e)
    sys.stdout.write(json.dumps(result) + "\n")
""".trimIndent()

@Serializable
internal data class ProbeOutput(val python: String, val robot: String? = null, val robotError: String? = null)

private val probeJson = Json { ignoreUnknownKeys = true }

/**
 * The state that the output of the probe stands for: a result, or a failed check when the probe did not run to the
 * end or printed something else.
 */
internal fun probeState(output: ProcessOutput): EnvironmentState {
    if (output.isTimeout) {
        return EnvironmentState.Failed(RobotCodeBundle.message("python.check.timeout"))
    }
    if (output.isCancelled || output.exitCode != 0) {
        return EnvironmentState.Failed(RobotCodeBundle.message("python.check.exitCode", output.exitCode.toString()))
    }
    val probe = output.stdout.lines().lastOrNull { it.isNotBlank() }?.let {
        try {
            probeJson.decodeFromString<ProbeOutput>(it)
        } catch (_: IllegalArgumentException) {
            null
        }
    } ?: return EnvironmentState.Failed(RobotCodeBundle.message("python.check.output"))
    return EnvironmentState.Checked(probeResult(probe))
}

internal fun probeResult(probe: ProbeOutput): EnvironmentResult {
    val python = versionNumbers(probe.python)
    if (python.size < 2 || isOlder(python, MINIMUM_PYTHON)) {
        return EnvironmentResult.PythonTooOld(python.take(2).joinToString("."))
    }
    val robot = probe.robot ?: return EnvironmentResult.RobotNotInstalled
    if (isOlder(versionNumbers(robot), MINIMUM_ROBOT)) {
        return EnvironmentResult.RobotTooOld(robot)
    }
    return EnvironmentResult.Usable
}

/**
 * The leading numbers of a version such as `3.9.18` or `6.1rc1`, up to the first part that does not start with a
 * digit.
 */
internal fun versionNumbers(version: String): List<Int> {
    return version.split('.').map { part -> part.takeWhile { it.isDigit() } }.takeWhile { it.isNotEmpty() }
        .map { it.toInt() }
}

private fun isOlder(version: List<Int>, minimum: List<Int>): Boolean {
    for ((index, required) in minimum.withIndex()) {
        val actual = version.getOrElse(index) { 0 }
        if (actual != required) {
            return actual < required
        }
    }
    return false
}
