package dev.robotcode.robotcode4ij


import org.jetbrains.plugins.textmate.api.TextMateBundleProvider

private val robotCodeBundle = getBundles()

private fun getBundles(): List<TextMateBundleProvider.PluginBundle> {
    return listOf(TextMateBundleProvider.PluginBundle("robotcode", BundledHelpers.basePath))
}

class RobotCodeTextMateBundleProvider : TextMateBundleProvider {
    
    override fun getBundles(): List<TextMateBundleProvider.PluginBundle> {
        return robotCodeBundle
    }
}
