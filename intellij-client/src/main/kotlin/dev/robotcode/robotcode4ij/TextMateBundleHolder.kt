package dev.robotcode.robotcode4ij

import org.jetbrains.plugins.textmate.TextMateService
import org.jetbrains.plugins.textmate.language.TextMateConcurrentMapInterner
import org.jetbrains.plugins.textmate.language.TextMateLanguageDescriptor
import org.jetbrains.plugins.textmate.language.syntax.TextMateSyntaxTableBuilder


object TextMateBundleHolder {
    private val interner = TextMateConcurrentMapInterner()

    val descriptor: TextMateLanguageDescriptor by lazy {

        val reader = TextMateService.getInstance().readBundle(RobotCodeHelpers.basePath)
            ?: throw IllegalStateException("Failed to read robotcode textmate bundle")

        val builder = TextMateSyntaxTableBuilder(interner)

        val grammarIterator = reader.readGrammars().iterator()
        while (grammarIterator.hasNext()) {
            val grammar = grammarIterator.next()

            val rootScopeName =  builder.addSyntax(grammar.plist.value) ?: continue
            if (rootScopeName == "source.robotframework") {
                val syntax = builder.build()
                return@lazy TextMateLanguageDescriptor(rootScopeName, syntax.getSyntax(rootScopeName))
            }
        }

        throw IllegalStateException("Failed to find robotcode textmate in bundle")
    }

}
