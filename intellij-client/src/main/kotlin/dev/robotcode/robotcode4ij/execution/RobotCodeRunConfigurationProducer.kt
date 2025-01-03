package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.actions.ConfigurationContext
import com.intellij.execution.actions.LazyRunConfigurationProducer
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.openapi.util.Ref
import com.intellij.psi.PsiElement
import com.intellij.psi.util.elementType
import dev.robotcode.robotcode4ij.psi.FILE
import dev.robotcode.robotcode4ij.psi.RobotSuiteFile
import dev.robotcode.robotcode4ij.psi.TESTCASE_NAME


class RobotCodeRunConfigurationProducer : LazyRunConfigurationProducer<RobotCodeRunConfiguration>() {
    override fun getConfigurationFactory(): ConfigurationFactory {
        return runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
    }
    
    override fun setupConfigurationFromContext(
        configuration: RobotCodeRunConfiguration,
        context: ConfigurationContext,
        sourceElement: Ref<PsiElement>
    ): Boolean {
        // TODO
        val psiElement = sourceElement.get()
        val psiFile = psiElement.containingFile as? RobotSuiteFile ?: return false
        val virtualFile = psiFile.virtualFile ?: return false
        
        when (psiElement.elementType) {
            TESTCASE_NAME -> {
                configuration.name = psiElement.text
                configuration.suite = virtualFile.url
                configuration.test = psiElement.text
                return true
            }
            
            FILE -> {
                configuration.name = virtualFile.presentableName
                configuration.suite = virtualFile.url
                return true
            }
            
            else -> return false
        }
    }
    
    override fun isConfigurationFromContext(
        configuration: RobotCodeRunConfiguration,
        context: ConfigurationContext
    ): Boolean {
        val psiElement = context.psiLocation
        val psiFile = psiElement?.containingFile as? RobotSuiteFile ?: return false
        val virtualFile = psiFile.virtualFile ?: return false
        
        return when (psiElement.elementType) {
            TESTCASE_NAME -> {
                configuration.suite == virtualFile.url && configuration.test == psiElement.text
            }
            
            FILE -> {
                configuration.suite == virtualFile.url
            }
            
            else -> false
        }
    }
}
