package dev.robotcode.robotcode4ij

import com.intellij.ide.browsers.BrowserLauncher
import com.intellij.ide.browsers.WebBrowser
import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.Project
import com.intellij.testFramework.replaceService
import java.io.File
import java.nio.file.Path

/** Takes the place of the IDE's browser launcher in a test and records the addresses it was asked to open. */
internal class RecordingBrowserLauncher : BrowserLauncher() {
    companion object {
        fun install(parentDisposable: Disposable): RecordingBrowserLauncher {
            return RecordingBrowserLauncher().also {
                ApplicationManager.getApplication().replaceService(BrowserLauncher::class.java, it, parentDisposable)
            }
        }
    }

    val urls: MutableList<String> = mutableListOf()

    override fun open(url: String) {
        urls += url
    }

    override fun browse(file: File) {
        urls += file.toURI().toString()
    }

    override fun browse(file: Path) {
        urls += file.toUri().toString()
    }

    override fun browse(url: String, browser: WebBrowser?, project: Project?) {
        urls += url
    }
}
