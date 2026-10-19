package dev.robotcode.robotcode4ij

import com.intellij.ide.plugins.DynamicPlugins
import com.intellij.ide.plugins.IdeaPluginDescriptorImpl
import com.intellij.ide.plugins.PluginManagerCore
import com.intellij.openapi.extensions.PluginId
import com.intellij.testFramework.fixtures.BasePlatformTestCase

/** Installing, updating and uninstalling RobotCode take effect after a restart of the IDE. */
class RobotCodePluginInstallationTest : BasePlatformTestCase() {

    fun testThePluginRequiresARestart() {
        val descriptor = PluginManagerCore.getPlugin(PluginId.getId("dev.robotcode.robotcode4ij"))

        assertTrue(descriptor is IdeaPluginDescriptorImpl)
        descriptor as IdeaPluginDescriptorImpl
        assertTrue(descriptor.isRequireRestart)
        val reason = DynamicPlugins.checkCanUnloadWithoutRestart(descriptor)
        assertNotNull(reason)
        assertTrue(reason, reason!!.contains("requiring restart"))
    }
}
