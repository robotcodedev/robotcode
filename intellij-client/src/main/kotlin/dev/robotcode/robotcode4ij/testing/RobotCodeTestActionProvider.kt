package dev.robotcode.robotcode4ij.testing

import com.intellij.execution.testframework.TestConsoleProperties
import com.intellij.execution.testframework.TestFrameworkRunningModel
import com.intellij.execution.testframework.ToggleModelAction
import com.intellij.execution.testframework.ToggleModelActionProvider
import com.intellij.icons.AllIcons
import com.intellij.util.config.BooleanProperty

class RobotCodeTestActionProvider : ToggleModelActionProvider {
    override fun createToggleModelAction(properties: TestConsoleProperties?): ToggleModelAction? {
        // TODO: Implement this method
        return RobotCodeToggleModelAction(properties)
    }
}

class RobotCodeToggleModelAction(properties: TestConsoleProperties?) : ToggleModelAction(
    "Toggle Something",
    "Description of Toggle Something",
    AllIcons.RunConfigurations.Application,
    properties,
    BooleanProperty("Something", false)
) {
    
    var myModel: TestFrameworkRunningModel? = null
    
    override fun setModel(model: TestFrameworkRunningModel?) {
        this.myModel = model
    }
    
    override fun isEnabled(): Boolean {
        
        return true
    }
}
