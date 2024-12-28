package dev.robotcode.robotcode4ij.settings

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.fileTypes.SyntaxHighlighterFactory
import com.intellij.openapi.options.colors.AttributesDescriptor
import com.intellij.openapi.options.colors.ColorDescriptor
import com.intellij.openapi.options.colors.ColorSettingsPage
import dev.robotcode.robotcode4ij.RobotColors
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import dev.robotcode.robotcode4ij.RobotIcons
import javax.swing.Icon

class RobotCodeColorSettingsPage : ColorSettingsPage {
    
    private val descriptors: Array<AttributesDescriptor> = arrayOf(
        AttributesDescriptor("Settings", RobotColors.HEADER),
        AttributesDescriptor("Test case name", RobotColors.TESTCASE_NAME),
        AttributesDescriptor("Keyword name", RobotColors.KEYWORD_NAME),
    )
    
    
    override fun getAttributeDescriptors(): Array<AttributesDescriptor> {
        return descriptors
    }
    
    override fun getColorDescriptors(): Array<ColorDescriptor> {
        return ColorDescriptor.EMPTY_ARRAY
    }
    
    override fun getDisplayName(): String {
        return "Robot Framework"
    }
    
    override fun getIcon(): Icon? {
        return RobotIcons.RobotCode
    }
    
    override fun getHighlighter(): SyntaxHighlighter {
        return SyntaxHighlighterFactory.getSyntaxHighlighter(RobotFrameworkLanguage.INSTANCE, null, null)
    }
    
    override fun getDemoText(): String {
        return "*** Test Cases *** "
    }
    
    override fun getAdditionalHighlightingTagToDescriptorMap(): MutableMap<String, TextAttributesKey>? {
        return null
    }
}
