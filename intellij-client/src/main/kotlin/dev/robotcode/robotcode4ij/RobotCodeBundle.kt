package dev.robotcode.robotcode4ij

import com.intellij.DynamicBundle
import org.jetbrains.annotations.NonNls
import org.jetbrains.annotations.PropertyKey

@NonNls
private const val BUNDLE = "messages.RobotCode"

object RobotCodeBundle {
    private val instance = DynamicBundle(RobotCodeBundle::class.java, BUNDLE)
    
    @JvmStatic
    fun message(@PropertyKey(resourceBundle = BUNDLE) key: String, vararg params: Any) =
        instance.getMessage(key, *params)
    
    @Suppress("unused")
    @JvmStatic
    fun messagePointer(@PropertyKey(resourceBundle = BUNDLE) key: String, vararg params: Any) =
        instance.getLazyMessage(key, *params)
}
