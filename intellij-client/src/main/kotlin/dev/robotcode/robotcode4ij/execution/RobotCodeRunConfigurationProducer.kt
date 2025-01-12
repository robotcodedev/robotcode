package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.actions.ConfigurationContext
import com.intellij.execution.actions.LazyRunConfigurationProducer
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.openapi.util.Ref
import com.intellij.psi.PsiElement
import dev.robotcode.robotcode4ij.testing.testManger


class RobotCodeRunConfigurationProducer : LazyRunConfigurationProducer<RobotCodeRunConfiguration>() {
    override fun getConfigurationFactory(): ConfigurationFactory {
        return runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
    }
    
    override fun setupConfigurationFromContext(
        configuration: RobotCodeRunConfiguration,
        context: ConfigurationContext,
        sourceElement: Ref<PsiElement>
    ): Boolean {
        val testItem = configuration.project.testManger.findTestItem(sourceElement.get()) ?: return false
        
        configuration.name = testItem.name
        configuration.includedTestItems = listOf(testItem)
        
        return true
    }
    
    override fun isConfigurationFromContext(
        configuration: RobotCodeRunConfiguration,
        context: ConfigurationContext
    ): Boolean {
        
        val psiElement = context.psiLocation ?: return false
        val testItem = configuration.project.testManger.findTestItem(psiElement) ?: return false
        
        return configuration.includedTestItems == listOf(testItem)
    }
}
