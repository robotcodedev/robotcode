package dev.robotcode.robotcode4ij.testing

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

class DataItemsTest {

    private fun discoverResult(testItemExtra: String) = """
        {
          "items": [
            {
              "type": "workspace",
              "id": "/project",
              "name": "project",
              "longname": "project",
              "children": [
                {
                  "type": "suite",
                  "id": "/project/metadata.robot;Metadata",
                  "name": "Metadata",
                  "longname": "Metadata",
                  "uri": "file:///project/metadata.robot",
                  "relSource": "metadata.robot",
                  "source": "/project/metadata.robot",
                  "children": [
                    {
                      "type": "test",
                      "id": "/project/metadata.robot;Metadata.With Metadata;2",
                      "name": "With Metadata",
                      "longname": "Metadata.With Metadata",
                      "lineno": 2,
                      "uri": "file:///project/metadata.robot",
                      "relSource": "metadata.robot",
                      "source": "/project/metadata.robot",
                      "range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 0}},
                      "tags": ["smoke"],
                      $testItemExtra
                    },
                    {
                      "type": "test",
                      "id": "/project/metadata.robot;Metadata.Without Metadata;6",
                      "name": "Without Metadata",
                      "longname": "Metadata.Without Metadata",
                      "lineno": 6
                    }
                  ]
                }
              ]
            }
          ],
          "supportsParseInclude": true
        }
    """.trimIndent()

    @Test
    fun decodesTestItemWithMetadata() {
        val result = Json.decodeFromString<RobotCodeDiscoverResult>(
            discoverResult(""""metadata": {"Issue": "4409", "Owner Team": "core"}""")
        )

        val tests = result.items!![0].children!![0].children!!

        assertEquals(mapOf("Issue" to "4409", "Owner Team" to "core"), tests[0].metadata)
        assertNull(tests[1].metadata)
    }

    // `RobotCodeTestManager` decodes the discover output with the default `Json`, which rejects keys the
    // model doesn't declare, so every key `robotcode discover` emits has to be a property of `RobotCodeTestItem`.
    @Test
    fun defaultJsonRejectsUnknownKeys() {
        assertThrows(SerializationException::class.java) {
            Json.decodeFromString<RobotCodeDiscoverResult>(discoverResult(""""notInTheModel": {"Issue": "4409"}"""))
        }
    }

    @Test
    fun metadataIsPartOfEquality() {
        val item = RobotCodeTestItem("test", "id", "name", "longname", metadata = mapOf("Issue" to "4409"))

        assertEquals(item, item.copy(metadata = mapOf("Issue" to "4409")))
        assertEquals(item.hashCode(), item.copy(metadata = mapOf("Issue" to "4409")).hashCode())
        assertNotEquals(item, item.copy(metadata = mapOf("Issue" to "4410")))
        assertNotEquals(item, item.copy(metadata = null))
    }
}
