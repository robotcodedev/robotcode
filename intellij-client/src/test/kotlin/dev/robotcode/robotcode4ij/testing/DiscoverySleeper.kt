package dev.robotcode.robotcode4ij.testing

import kotlin.system.exitProcess

/**
 * A process that stands for a discovery that does not end: it sleeps for a minute. With an exit code as argument, it
 * ends at once with that code, without reading its input.
 */
object DiscoverySleeper {
    @JvmStatic
    fun main(args: Array<String>) {
        args.firstOrNull()?.let { exitProcess(it.toInt()) }
        Thread.sleep(60_000)
    }
}
