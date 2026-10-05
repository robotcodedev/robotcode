package dev.robotcode.robotcode4ij.configuration

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.highlighting.Colors

class RobotCodeColorSettingsPageTest : BasePlatformTestCase() {
    
    private val page = RobotCodeColorSettingsPage()
    
    fun testParameterAndTypeHintSettingsAreListed() {
        val keys = page.attributeDescriptors.map { it.key }
        assertContainsElements(keys, Colors.PARAMETER, Colors.TYPE_HINT)
    }
    
    fun testEveryDemoTagHasASetting() {
        val tags = Regex("<(\\w+)>").findAll(page.demoText).map { it.groupValues[1] }.toSet()
        assertEquals(setOf("parameter", "type_hint"), tags)
        assertEquals(tags, page.additionalHighlightingTagToDescriptorMap.keys)
    }
}
