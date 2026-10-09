package dev.robotcode.robotcode4ij.testing

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
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

    // `RobotCodeTestManager` ignores keys that the model does not declare, so a newer robotcode does not make the result
    // unreadable
    @Test
    fun unknownKeysAreIgnored() {
        val metadata = """"metadata": {"Issue": "4409"}"""

        assertEquals(
            decodeDiscoverResult(discoverResult(metadata)),
            decodeDiscoverResult(discoverResult("""$metadata, "notInTheModel": {"Issue": "4409"}"""))
        )
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
