package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/**
 * The profile list of `robot.toml` without a selection, which the warning of run configurations and the actions that
 * run once with a profile use. [read] reads it in [scope]; a list that could not be read is not cached.
 */
internal class ProfileListCache(
    private val scope: CoroutineScope,
    private val read: suspend () -> ProfileListResult?
) {
    @Volatile
    private var list: ProfileList? = null

    private var reading: Job? = null

    // a read that a clear overtook does not fill the cache
    private var generation = 0

    /** The cached list, or null while none has been read since the cache was cleared. */
    val cached: ProfileList?
        get() = list

    /** Starts reading the list unless it is cached or being read, and returns the job that reads it. */
    @Synchronized
    fun readInBackground(): Job? {
        if (list != null || reading?.isActive == true) {
            return null
        }
        val started = generation
        return scope.launch {
            val result = read() as? ProfileListResult.Read ?: return@launch
            synchronized(this@ProfileListCache) {
                if (generation == started) {
                    list = result.list
                }
            }
        }.also { reading = it }
    }

    /** Caches a list that was read elsewhere. */
    @Synchronized
    fun store(list: ProfileList) {
        this.list = list
    }

    /** Forgets the list. */
    @Synchronized
    fun clear() {
        generation++
        reading?.cancel()
        reading = null
        list = null
    }

    /** Forgets the list and reads it again, as when the language server has started after a change to `robot.toml`. */
    @Synchronized
    fun reload(): Job? {
        clear()
        return readInBackground()
    }
}

// The platform cancels the scope when the project closes or the plugin is unloaded.
@Service(Service.Level.PROJECT)
private class RobotCodeProfileListService(project: Project, scope: CoroutineScope) {
    val cache = ProfileListCache(scope) { project.readProfileListInBackground(listOf()) }
}

/** The cached profile list of the project. */
internal val Project.profileListCache: ProfileListCache
    get() = service<RobotCodeProfileListService>().cache
