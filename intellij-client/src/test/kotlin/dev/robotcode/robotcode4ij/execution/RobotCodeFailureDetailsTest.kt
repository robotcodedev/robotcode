package dev.robotcode.robotcode4ij.execution

import com.google.gson.Gson
import dev.robotcode.robotcode4ij.debugging.RobotEnqueuedArguments
import dev.robotcode.robotcode4ij.debugging.RobotExecutionEventArguments
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeFailureDetailsTest {

    // a robotEnded body as the listener sends it with Robot Framework 7.5: `Should Be Equal` failed inside the user
    // keyword `Build Greeting` of `common.resource`; the failed keywords come outermost first, with their call sites
    private val failedInAKeyword = """
        {
          "type": "test", "id": "/project/tests/sample.robot;Tests.Sample.Third Test Fails;6",
          "name": "Third Test Fails", "parentId": "/project/tests/sample.robot;Tests.Sample",
          "attributes": {
            "id": "s1-s1-t3", "longname": "Tests.Sample.Third Test Fails", "originalname": "Third Test Fails",
            "doc": "", "tags": [], "template": "", "source": "/project/tests/sample.robot", "lineno": 6,
            "starttime": "20261015 10:00:00.000", "endtime": "20261015 10:00:00.004", "elapsedtime": 4,
            "status": "FAIL", "message": "Hello, Robot != Hello, World"
          },
          "failedKeywords": [
            {
              "message": "Hello, Robot != Hello, World", "type": "KEYWORD", "kwname": "Build Greeting",
              "libname": "common", "doc": "", "args": ["Robot"], "assign": ["${'$'}{greeting}"], "tags": [],
              "timeout": null, "source": "/project/tests/sample.robot", "lineno": 7, "status": "FAIL",
              "starttime": "20261015 10:00:00.001", "endtime": "20261015 10:00:00.003", "elapsedtime": 2
            },
            {
              "message": "Hello, Robot != Hello, World", "type": "KEYWORD", "kwname": "Should Be Equal",
              "libname": "BuiltIn", "doc": "", "args": ["${'$'}{greeting}", "Hello, World"], "assign": [],
              "tags": [], "timeout": null, "source": "/project/resources/common.resource", "lineno": 4,
              "status": "FAIL", "starttime": "20261015 10:00:00.002", "endtime": "20261015 10:00:00.002",
              "elapsedtime": 0
            }
          ]
        }
    """.trimIndent()

    private fun decoded(body: String) = Gson().fromJson(body, RobotExecutionEventArguments::class.java)

    @Test
    fun theFailedKeywordsBecomeTheStackTraceInnermostFirst() {
        assertEquals(
            "    at BuiltIn.Should Be Equal (/project/resources/common.resource:4)\n" +
                "    at common.Build Greeting (/project/tests/sample.robot:7)",
            failureStackTrace(decoded(failedInAKeyword).failedKeywords)
        )
    }

    @Test
    fun aKeywordWithoutLibraryHasItsNameAlone() {
        val event = decoded(failedInAKeyword.replace("\"libname\": \"common\"", "\"libname\": \"\""))

        assertEquals(
            "    at BuiltIn.Should Be Equal (/project/resources/common.resource:4)\n" +
                "    at Build Greeting (/project/tests/sample.robot:7)",
            failureStackTrace(event.failedKeywords)
        )
    }

    @Test
    fun aTestThatFailedOutsideAKeywordHasNoStackTrace() {
        val withoutKeywords = failedInAKeyword.substringBefore(",\n  \"failedKeywords\"") + "\n}"

        assertNull(failureStackTrace(decoded(withoutKeywords).failedKeywords))
        assertNull(failureStackTrace(arrayOf()))
    }

    // a robotEnded body in which the test caught a failure with TRY/EXCEPT and one with Run Keyword And Ignore Error
    // in `Check Value`, before it failed in `Check Value`; the listener marks the caught ones
    private val caughtBefore = """
        {
          "type": "test", "id": "/project/tests/caught.robot;Tests.Caught.Caught Before;2", "name": "Caught Before",
          "attributes": {
            "longname": "Tests.Caught.Caught Before", "source": "/project/tests/caught.robot", "lineno": 2,
            "status": "FAIL", "message": "1 != 0"
          },
          "failedKeywords": [
            {
              "message": "1 != 0", "type": "KEYWORD", "kwname": "Check Value", "libname": "",
              "source": "/project/tests/caught.robot", "lineno": 9, "status": "FAIL"
            },
            {
              "message": "1 != 0", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/tests/caught.robot", "lineno": 14, "status": "FAIL"
            },
            {
              "message": "x != 0", "type": "KEYWORD", "kwname": "Check Value", "libname": "",
              "source": "/project/tests/caught.robot", "lineno": 8, "status": "FAIL", "caught": true
            },
            {
              "message": "x != 0", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/tests/caught.robot", "lineno": 14, "status": "FAIL", "caught": true
            },
            {
              "message": "a != b\nwith a second line", "type": "KEYWORD", "kwname": "Should Be Equal",
              "libname": "BuiltIn", "source": "/project/tests/caught.robot", "lineno": 4, "status": "FAIL",
              "caught": true
            }
          ]
        }
    """.trimIndent()

    @Test
    fun caughtFailuresFollowTheFailureEachUnderItsMessage() {
        assertEquals(
            "    at BuiltIn.Should Be Equal (/project/tests/caught.robot:14)\n" +
                "    at Check Value (/project/tests/caught.robot:9)\n" +
                "Caught: a != b\n" +
                "    at BuiltIn.Should Be Equal (/project/tests/caught.robot:4)\n" +
                "Caught: x != 0\n" +
                "    at BuiltIn.Should Be Equal (/project/tests/caught.robot:14)\n" +
                "    at Check Value (/project/tests/caught.robot:8)",
            failureStackTrace(decoded(caughtBefore).failedKeywords)
        )
    }

    @Test
    fun navigatingUsesTheLinesBeforeTheCaughtFailures() {
        val trace = failureStackTrace(decoded(caughtBefore).failedKeywords)!!

        assertEquals(
            "    at BuiltIn.Should Be Equal (/project/tests/caught.robot:14)\n" +
                "    at Check Value (/project/tests/caught.robot:9)",
            failurePathOf(trace)
        )
        // a test whose only failed keywords were caught navigates to its own line
        assertEquals("", failurePathOf("Caught: a != b\n    at BuiltIn.Should Be Equal (/project/tests/caught.robot:4)"))
        assertEquals("", failurePathOf("Caught\n    at BuiltIn.Fail (/project/tests/caught.robot:4)"))
    }

    // a robotEnqueued body as the listener sends it for a folder with two suite files and a task file, whose source
    // path has spaces; Robot Framework left out the test that the tag options of robot.toml exclude
    private val enqueued = """
        {
          "items": [
            "/home/me/my project/tests;Tests",
            "/home/me/my project/tests/first.robot;Tests.First",
            "/home/me/my project/tests/first.robot;Tests.First.One;3",
            "/home/me/my project/tests/first.robot;Tests.First.Two;7",
            "/home/me/my project/tests/nested;Tests.Nested",
            "/home/me/my project/tests/nested/second.robot;Tests.Nested.Second",
            "/home/me/my project/tests/nested/second.robot;Tests.Nested.Second.Three;2",
            "/home/me/my project/tests/tasks.robot;Tests.Tasks",
            "/home/me/my project/tests/tasks.robot;Tests.Tasks.Clean Up;4"
          ]
        }
    """.trimIndent()

    @Test
    fun theTestsAndTasksOfTheRunAreCounted() {
        val items = Gson().fromJson(enqueued, RobotEnqueuedArguments::class.java).items

        assertEquals(4, enqueuedTestCount(items))
        assertEquals(0, enqueuedTestCount(arrayOf()))
        assertEquals(0, enqueuedTestCount(null))
    }
}
