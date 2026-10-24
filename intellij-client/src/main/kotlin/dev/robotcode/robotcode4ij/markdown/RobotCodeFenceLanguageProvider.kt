package dev.robotcode.robotcode4ij.markdown

import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.lookup.LookupElement
import com.intellij.lang.Language
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import org.intellij.plugins.markdown.injection.CodeFenceLanguageProvider

// the words VS Code's code block grammar starts Robot Framework code at, in any case
private val ROBOT_FRAMEWORK_INFO_WORDS = setOf("robot", "robotframework")

/** Treats Markdown code blocks marked `robot` or `robotframework`, in any case, as Robot Framework code. */
class RobotCodeFenceLanguageProvider : CodeFenceLanguageProvider {
    override fun getLanguageByInfoString(infoString: String): Language? {
        // the info string comes as written, also with attributes after the language
        val word = infoString.trim().split(Regex("\\s+"), limit = 2).first()
        return if (word.lowercase() in ROBOT_FRAMEWORK_INFO_WORDS) RobotFrameworkLanguage else null
    }

    override fun getCompletionVariantsForInfoString(parameters: CompletionParameters): List<LookupElement> =
        emptyList()
}
