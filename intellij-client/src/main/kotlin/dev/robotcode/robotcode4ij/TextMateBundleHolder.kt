package dev.robotcode.robotcode4ij

import com.intellij.util.containers.Interner
import org.jetbrains.plugins.textmate.TextMateService
import org.jetbrains.plugins.textmate.language.TextMateLanguageDescriptor
import org.jetbrains.plugins.textmate.language.syntax.TextMateSyntaxTable


object TextMateBundleHolder {
    private val interner = Interner.createWeakInterner<CharSequence>()
    
    val descriptor: TextMateLanguageDescriptor by lazy {
        
        val reader = TextMateService.getInstance().readBundle(RobotCodeHelpers.basePath)
            ?: throw IllegalStateException("Failed to read robotcode textmate bundle")
        
        val syntaxTable = TextMateSyntaxTable()
        
        val grammarIterator = reader.readGrammars().iterator()
        while (grammarIterator.hasNext()) {
            val grammar = grammarIterator.next()
            val rootScopeName = syntaxTable.loadSyntax(grammar.plist.value, interner) ?: continue
            if (rootScopeName == "source.robotframework") {
                val syntax = syntaxTable.getSyntax(rootScopeName)
                return@lazy TextMateLanguageDescriptor(rootScopeName, syntax)
            }
        }
        
        throw IllegalStateException("Failed to find robotcode textmate in bundle")
    }
    
}
