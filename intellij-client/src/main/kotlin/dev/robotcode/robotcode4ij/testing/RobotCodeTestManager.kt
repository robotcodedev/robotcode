package dev.robotcode.robotcode4ij.testing

import com.intellij.execution.process.CapturingProcessHandler
import com.intellij.execution.process.CapturingProcessRunner
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement

@Serializable data class Position(val line: UInt, val character: UInt)

@Serializable data class Range(val start: Position, val end: Position)

@Serializable data class RobotCodeTestItem(
    val type: String,
    val id: String,
    val name: String,
    val longname: String,
    val description: String? = null,
    val uri: String? = null,
    val relSource: String? = null,
    val source: String? = null,
    val needsParseInclude: Boolean? = null,
    val children: Array<RobotCodeTestItem>? = null,
    val range: Range? = null,
    val error: String? = null,
    val tags: Array<String>? = null,
    val rpa: Boolean? = null
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        
        other as RobotCodeTestItem
        
        if (needsParseInclude != other.needsParseInclude) return false
        if (type != other.type) return false
        if (id != other.id) return false
        if (name != other.name) return false
        if (longname != other.longname) return false
        if (description != other.description) return false
        if (uri != other.uri) return false
        if (relSource != other.relSource) return false
        if (children != null) {
            if (other.children == null) return false
            if (!children.contentEquals(other.children)) return false
        } else if (other.children != null) return false
        if (range != other.range) return false
        if (error != other.error) return false
        if (tags != null) {
            if (other.tags == null) return false
            if (!tags.contentEquals(other.tags)) return false
        } else if (other.tags != null) return false
        
        return true
    }
    
    override fun hashCode(): Int {
        var result = needsParseInclude?.hashCode() ?: 0
        result = 31 * result + type.hashCode()
        result = 31 * result + id.hashCode()
        result = 31 * result + name.hashCode()
        result = 31 * result + longname.hashCode()
        result = 31 * result + description.hashCode()
        result = 31 * result + (uri?.hashCode() ?: 0)
        result = 31 * result + (relSource?.hashCode() ?: 0)
        result = 31 * result + (children?.contentHashCode() ?: 0)
        result = 31 * result + (range?.hashCode() ?: 0)
        result = 31 * result + (error?.hashCode() ?: 0)
        result = 31 * result + (tags?.contentHashCode() ?: 0)
        return result
    }
}

@Serializable data class RobotCodeDiscoverResult(
    val items: Array<RobotCodeTestItem>? = null,
    val diagnostics: Map<String, JsonElement>? = null // TODO val diagnostics: { [Key: string]: Diagnostic[] };
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        
        other as RobotCodeDiscoverResult
        
        if (items != null) {
            if (other.items == null) return false
            if (!items.contentEquals(other.items)) return false
        } else if (other.items != null) return false
        if (diagnostics != other.diagnostics) return false
        
        return true
    }
    
    override fun hashCode(): Int {
        var result = items?.contentHashCode() ?: 0
        result = 31 * result + (diagnostics?.hashCode() ?: 0)
        return result
    }
}

@Service(Service.Level.PROJECT) class RobotCodeTestManager(private val project: Project) {
    var testItems: Array<RobotCodeTestItem> = arrayOf()
        private set
    
    fun refresh() {
        // TODO: Add support for configurable paths
        val defaultPaths = arrayOf("--default-path", ".")
        
        try {
            val cmdLine = project.buildRobotCodeCommandLine(
                arrayOf(*defaultPaths, "discover", "all"), format = "json"
            )
            
            testItems = ApplicationManager.getApplication().executeOnPooledThread<RobotCodeDiscoverResult> {
                val result = CapturingProcessRunner(CapturingProcessHandler(cmdLine)).runProcess()
                if (result.exitCode != 0) {
                    throw RuntimeException("Failed to discover test items: ${result.stderr}")
                }
                Json.decodeFromString<RobotCodeDiscoverResult>(result.stdout)
            }.get().items ?: arrayOf()
        } catch (e: Exception) {
            thisLogger().warn("Failed to discover test items", e)
        }
    }
}

val Project.testManger: RobotCodeTestManager
    get() {
        return this.service<RobotCodeTestManager>()
    }
