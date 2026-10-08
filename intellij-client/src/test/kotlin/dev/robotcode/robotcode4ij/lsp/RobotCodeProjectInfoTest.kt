package dev.robotcode.robotcode4ij.lsp

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeProjectInfoTest {

    @Test
    fun answerIsDecodedWithAndWithoutRobocop() {
        val withRobocop = Gson().fromJson(
            """{"robotVersionString": "7.5", "robocopVersionString": "9.0.0",""" +
                """ "pythonVersionString": "3.14.0 (main, Oct 7 2025)", "pythonExecutable": "/opt/py/bin/python",""" +
                """ "robotCodeVersionString": "2.7.0"}""",
            ProjectInfo::class.java
        )
        val withoutRobocop = Gson().fromJson("""{"robotVersionString": "7.5"}""", ProjectInfo::class.java)

        assertEquals(ProjectInfo("7.5", "9.0.0", "3.14.0 (main, Oct 7 2025)", "/opt/py/bin/python", "2.7.0"), withRobocop)
        assertEquals("7.5", withoutRobocop.robotVersionString)
        assertNull(withoutRobocop.robocopVersionString)
    }
}
