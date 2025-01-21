package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.actions.ConfigurationContext
import com.intellij.execution.actions.ConfigurationFromContext
import com.intellij.execution.actions.LazyRunConfigurationProducer
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.openapi.util.Ref
import com.intellij.psi.PsiElement
import com.redhat.devtools.lsp4ij.features.documentSymbol.DocumentSymbolData
import dev.robotcode.robotcode4ij.testing.testManger
import java.util.*

fun DocumentSymbolData.toPsiElement(): PsiElement? {
    val file = this.containingFile
    return file.findElementAt(textOffset)
}

class RobotCodeRunConfigurationProducer : LazyRunConfigurationProducer<RobotCodeRunConfiguration>() {
    override fun getConfigurationFactory(): ConfigurationFactory {
        return runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
    }
    
    override fun setupConfigurationFromContext(
        configuration: RobotCodeRunConfiguration,
        context: ConfigurationContext,
        sourceElement: Ref<PsiElement>
    ): Boolean {
        var psiElement = sourceElement.get()
        if (psiElement is DocumentSymbolData) {
            psiElement = psiElement.toPsiElement() ?: return false
        }
        val testItem = configuration.project.testManger.findTestItem(psiElement) ?: return false
        
        configuration.name = "${
            testItem.type.replaceFirstChar {
                if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it
                    .toString()
            }
        } ${testItem.name}"
        
        if (testItem.type != "workspace") {
            configuration.includedTestItems = listOf(testItem)
        }
        
        return true
    }
    
    override fun isConfigurationFromContext(
        configuration: RobotCodeRunConfiguration,
        context: ConfigurationContext
    ): Boolean {
        var psiElement = context.psiLocation ?: return false
        if (psiElement is DocumentSymbolData) {
            psiElement = psiElement.toPsiElement() ?: return false
        }
        val testItem = configuration.project.testManger.findTestItem(psiElement) ?: return false
        
        if (testItem.type == "workspace") {
            return configuration.includedTestItems.isEmpty()
        }
        return configuration.includedTestItems == listOf(testItem)
    }
    
    override fun isPreferredConfiguration(self: ConfigurationFromContext?, other: ConfigurationFromContext?): Boolean {
        return false
    }
    
}
