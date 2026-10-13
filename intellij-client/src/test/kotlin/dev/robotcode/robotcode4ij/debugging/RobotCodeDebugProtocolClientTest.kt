package dev.robotcode.robotcode4ij.debugging

import com.jetbrains.rd.util.lifetime.Lifetime
import org.eclipse.lsp4j.debug.ContinuedEventArguments
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeDebugProtocolClientTest {

    @Test
    fun aContinuedEventIsPassedOnToTheSignal() {
        val client = RobotCodeDebugProtocolClient()
        val received = mutableListOf<ContinuedEventArguments>()
        client.onContinued.advise(Lifetime.Eternal) { received.add(it) }

        val event = ContinuedEventArguments().apply { threadId = 0; allThreadsContinued = true }
        client.continued(event)

        assertEquals(listOf(event), received)
    }
}
