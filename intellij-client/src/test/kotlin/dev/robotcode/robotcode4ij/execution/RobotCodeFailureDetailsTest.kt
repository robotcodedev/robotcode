package dev.robotcode.robotcode4ij.execution

import com.google.gson.Gson
import dev.robotcode.robotcode4ij.debugging.RobotEnqueuedArguments
import dev.robotcode.robotcode4ij.debugging.RobotExecutionEventArguments
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeFailureDetailsTest {

    // a robotEnded body as the listener sends it with Robot Framework 7.5: `Should Be Equal` failed inside the user
    // keyword `Build Greeting` of `common.resource`; the failed keywords come outermost first, with their call sites,
    // and the failure gives its calls innermost first
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
          ],
          "failures": [{"keyword": 1, "calls": [1, 0]}]
        }
    """.trimIndent()

    private fun decoded(body: String) = Gson().fromJson(body, RobotExecutionEventArguments::class.java)

    private fun trace(body: String) = decoded(body).let { failureStackTrace(it.failedKeywords, it.failures) }

    @Test
    fun aFailureListsItsCallsFromTheTestInward() {
        assertEquals(
            "  File \"/project/tests/sample.robot\", line 7, in common.Build Greeting\n" +
                "  File \"/project/resources/common.resource\", line 4, in BuiltIn.Should Be Equal",
            trace(failedInAKeyword)
        )
    }

    @Test
    fun aKeywordWithoutLibraryHasItsNameAlone() {
        assertEquals(
            "  File \"/project/tests/sample.robot\", line 7, in Build Greeting\n" +
                "  File \"/project/resources/common.resource\", line 4, in BuiltIn.Should Be Equal",
            trace(failedInAKeyword.replace("\"libname\": \"common\"", "\"libname\": \"\""))
        )
    }

    @Test
    fun aTestWithoutFailuresHasNoStackTrace() {
        val withoutKeywords = failedInAKeyword.substringBefore(",\n  \"failedKeywords\"") + "\n}"

        assertNull(trace(withoutKeywords))
        assertNull(failureStackTrace(arrayOf(), arrayOf()))
        assertNull(failureStackTrace(decoded(failedInAKeyword).failedKeywords, null))
    }

    // a robotEnded body in which a step of the test failed, and then its teardown
    private val bodyAndTeardown = """
        {
          "type": "test", "id": "/project/tests/sample.robot;Tests.Sample.Body And Teardown;8",
          "name": "Body And Teardown",
          "attributes": {
            "longname": "Tests.Sample.Body And Teardown", "source": "/project/tests/sample.robot", "lineno": 8,
            "status": "FAIL", "message": "a != b\n\nAlso teardown failed:\nc != d"
          },
          "failedKeywords": [
            {
              "message": "c != d", "type": "TEARDOWN", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/tests/sample.robot", "lineno": 10, "status": "FAIL"
            },
            {
              "message": "a != b", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/tests/sample.robot", "lineno": 9, "status": "FAIL"
            }
          ],
          "failures": [{"keyword": 1, "calls": [1]}, {"keyword": 0, "calls": [0]}]
        }
    """.trimIndent()

    @Test
    fun severalFailuresFollowAnEmptyLineAndEachBeginWithItsMessage() {
        assertEquals(
            "\n" +
                "a != b\n" +
                "  File \"/project/tests/sample.robot\", line 9, in BuiltIn.Should Be Equal\n" +
                "c != d\n" +
                "  File \"/project/tests/sample.robot\", line 10, in BuiltIn.Should Be Equal",
            trace(bodyAndTeardown)
        )
    }

    // a robotEnded body as the listener sends it with Robot Framework 7.5: `Collect Two` of `common.resource`, tagged
    // `robot:continue-on-failure`, failed in both of its `Should Be Equal`
    private val collects = """
        {
          "type": "test", "id": "/project/tests/sample.robot;Tests.Sample.Collects;18", "name": "Collects",
          "attributes": {
            "longname": "Tests.Sample.Collects", "source": "/project/tests/sample.robot", "lineno": 18,
            "status": "FAIL", "message": "Several failures occurred:\n\n1) c != d\n\n2) e != f"
          },
          "failedKeywords": [
            {
              "message": "e != f", "type": "KEYWORD", "kwname": "Collect Two", "libname": "common",
              "source": "/project/tests/sample.robot", "lineno": 19, "status": "FAIL"
            },
            {
              "message": "e != f", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/resources/common.resource", "lineno": 13, "status": "FAIL"
            },
            {
              "message": "c != d", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/resources/common.resource", "lineno": 12, "status": "FAIL"
            }
          ],
          "failures": [{"keyword": 2, "calls": [2, 0]}, {"keyword": 1, "calls": [1, 0]}]
        }
    """.trimIndent()

    @Test
    fun aKeywordThatCollectsFailuresIsInEachOfThem() {
        assertEquals(
            "\n" +
                "c != d\n" +
                "  File \"/project/tests/sample.robot\", line 19, in common.Collect Two\n" +
                "  File \"/project/resources/common.resource\", line 12, in BuiltIn.Should Be Equal\n" +
                "e != f\n" +
                "  File \"/project/tests/sample.robot\", line 19, in common.Collect Two\n" +
                "  File \"/project/resources/common.resource\", line 13, in BuiltIn.Should Be Equal",
            trace(collects)
        )
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
          ],
          "failures": [{"keyword": 4, "calls": [4]}, {"keyword": 3, "calls": [3, 2]}, {"keyword": 1, "calls": [1, 0]}]
        }
    """.trimIndent()

    @Test
    fun caughtFailuresFollowTheFailureEachUnderItsMessage() {
        assertEquals(
            "  File \"/project/tests/caught.robot\", line 9, in Check Value\n" +
                "  File \"/project/tests/caught.robot\", line 14, in BuiltIn.Should Be Equal\n" +
                "Caught: a != b\n" +
                "  File \"/project/tests/caught.robot\", line 4, in BuiltIn.Should Be Equal\n" +
                "Caught: x != 0\n" +
                "  File \"/project/tests/caught.robot\", line 8, in Check Value\n" +
                "  File \"/project/tests/caught.robot\", line 14, in BuiltIn.Should Be Equal",
            trace(caughtBefore)
        )
    }

    // a robotEnded body in which Wait Until Keyword Succeeds failed after its third attempt: its failure has the calls
    // of the last attempt, whose `Should Be Equal` has the line of the call of Wait Until Keyword Succeeds
    private val retried = """
        {
          "type": "test", "id": "/project/tests/sample.robot;Tests.Sample.Retries Fail;12", "name": "Retries Fail",
          "attributes": {
            "longname": "Tests.Sample.Retries Fail", "source": "/project/tests/sample.robot", "lineno": 12,
            "status": "FAIL",
            "message": "Keyword 'Should Be Equal' failed after retrying 3 times. The last error was: a != b"
          },
          "failedKeywords": [
            {
              "message": "Keyword 'Should Be Equal' failed after retrying 3 times. The last error was: a != b",
              "type": "KEYWORD", "kwname": "Wait Until Keyword Succeeds", "libname": "BuiltIn",
              "source": "/project/tests/sample.robot", "lineno": 13, "status": "FAIL"
            },
            {
              "message": "a != b", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/tests/sample.robot", "lineno": 13, "status": "FAIL"
            },
            {
              "message": "a != b", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/tests/sample.robot", "lineno": 13, "status": "FAIL"
            },
            {
              "message": "a != b", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/tests/sample.robot", "lineno": 13, "status": "FAIL"
            }
          ],
          "failures": [{"keyword": 0, "calls": [1, 0]}]
        }
    """.trimIndent()

    @Test
    fun aRetriedKeywordIsOneFailure() {
        assertEquals(
            "  File \"/project/tests/sample.robot\", line 13, in BuiltIn.Wait Until Keyword Succeeds",
            trace(retried)
        )
    }

    // a robotEnded body in which `Check Value`, which Run Keyword And Continue On Failure ran and which has its line,
    // failed in `Should Be Equal`
    private val runKeyword = """
        {
          "type": "test", "id": "/project/tests/sample.robot;Tests.Sample.Run Keyword Line;15",
          "name": "Run Keyword Line",
          "attributes": {
            "longname": "Tests.Sample.Run Keyword Line", "source": "/project/tests/sample.robot", "lineno": 15,
            "status": "FAIL", "message": "1 != ok"
          },
          "failedKeywords": [
            {
              "message": "1 != ok", "type": "KEYWORD", "kwname": "Run Keyword And Continue On Failure",
              "libname": "BuiltIn", "source": "/project/tests/sample.robot", "lineno": 16, "status": "FAIL"
            },
            {
              "message": "1 != ok", "type": "KEYWORD", "kwname": "Check Value", "libname": "common",
              "source": "/project/tests/sample.robot", "lineno": 16, "status": "FAIL"
            },
            {
              "message": "1 != ok", "type": "KEYWORD", "kwname": "Should Be Equal", "libname": "BuiltIn",
              "source": "/project/resources/common.resource", "lineno": 8, "status": "FAIL"
            }
          ],
          "failures": [{"keyword": 2, "calls": [2, 1, 0]}]
        }
    """.trimIndent()

    @Test
    fun aCallOnTheLineOfTheCallItRanInIsLeftOut() {
        assertEquals(
            "  File \"/project/tests/sample.robot\", line 16, in BuiltIn.Run Keyword And Continue On Failure\n" +
                "  File \"/project/resources/common.resource\", line 8, in BuiltIn.Should Be Equal",
            trace(runKeyword)
        )
    }

    @Test
    fun navigatingUsesTheCallsBeforeTheCaughtFailures() {
        assertEquals(
            "  File \"/project/tests/caught.robot\", line 9, in Check Value\n" +
                "  File \"/project/tests/caught.robot\", line 14, in BuiltIn.Should Be Equal",
            failurePathOf(trace(caughtBefore)!!)
        )
        // without the empty line and the message lines of several failures, so that a location at the end of a message
        // is no target
        val located = bodyAndTeardown.replace(
            "\"a != b\", \"type\"", "\"a != b (/project/tests/sample.robot:3)\", \"type\""
        )
        assertEquals(
            "  File \"/project/tests/sample.robot\", line 9, in BuiltIn.Should Be Equal\n" +
                "  File \"/project/tests/sample.robot\", line 10, in BuiltIn.Should Be Equal",
            failurePathOf(trace(located)!!)
        )
        // a test whose only failed keywords were caught navigates to its own line
        assertEquals(
            "",
            failurePathOf("Caught: a != b\n  File \"/project/tests/caught.robot\", line 4, in BuiltIn.Should Be Equal")
        )
        assertEquals("", failurePathOf("Caught\n  File \"/project/tests/caught.robot\", line 4, in BuiltIn.Fail"))
    }

    // IntelliJ opens the first location that the console filter finds in the lines it gets
    private fun firstLocation(lines: String) = lines.lineSequence()
        .firstNotNullOfOrNull { consoleLinks(it) { true }.firstOrNull() }
        ?.let { it.path to it.line }

    @Test
    fun navigatingOpensTheCallInTheTestThatLedToTheFirstFailure() {
        assertEquals("/project/tests/sample.robot" to 7, firstLocation(failurePathOf(trace(failedInAKeyword)!!)))
        assertEquals("/project/tests/sample.robot" to 9, firstLocation(failurePathOf(trace(bodyAndTeardown)!!)))
        assertEquals("/project/tests/caught.robot" to 9, firstLocation(failurePathOf(trace(caughtBefore)!!)))
    }

    // a robotEnqueued body as the listener sends it for a folder with two suite files, a task file and the suite file of
    // a custom parser, whose source path has spaces; Robot Framework left out the test that the tag options of
    // robot.toml exclude, and the custom parser's test has no line number, so its ID ends in 0
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
            "/home/me/my project/tests/tasks.robot;Tests.Tasks.Clean Up;4",
            "/home/me/my project/tests/example.example;Tests.Example",
            "/home/me/my project/tests/example.example;Tests.Example.Without Line;0"
          ]
        }
    """.trimIndent()

    @Test
    fun theTestsAndTasksOfTheRunAreCounted() {
        val items = Gson().fromJson(enqueued, RobotEnqueuedArguments::class.java).items

        assertEquals(5, enqueuedTestCount(items))
        assertEquals(0, enqueuedTestCount(arrayOf()))
        assertEquals(0, enqueuedTestCount(null))
    }
}
