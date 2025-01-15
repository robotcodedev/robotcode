package dev.robotcode.robotcode4ij.testing

import com.intellij.codeInsight.daemon.DaemonCodeAnalyzer
import com.intellij.execution.process.CapturingProcessHandler
import com.intellij.execution.process.CapturingProcessRunner
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.PsiDirectory
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.util.elementType
import com.intellij.psi.util.startOffset
import com.intellij.util.io.URLUtil
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import dev.robotcode.robotcode4ij.psi.IRobotFrameworkElementType
import dev.robotcode.robotcode4ij.psi.RobotSuiteFile
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import java.net.URI

@Serializable data class Position(val line: UInt, val character: UInt)

@Serializable data class Range(val start: Position, val end: Position)

@Serializable data class RobotCodeTestItem(
    val type: String,
    val id: String,
    val name: String,
    val longname: String,
    val lineno: Int? = null,
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
        
        DaemonCodeAnalyzer.getInstance(project).restart()
    }
    
    fun findTestItem(
        uri: String,
        line: UInt? = null,
    ): RobotCodeTestItem? {
        return findTestItem(testItems, uri, line)
    }
    
    fun findTestItem(
        root: RobotCodeTestItem,
        uri: String,
        line: UInt? = null,
    ): RobotCodeTestItem? {
        
        if (line == null) {
            if (root.uri == uri) {
                return root
            }
        } else {
            if (root.uri == uri && root.range != null && root.range.start.line == line) {
                return root
            }
        }
        
        return findTestItem(root.children ?: arrayOf(), uri, line)
    }
    
    fun findTestItem(
        testItems: Array<RobotCodeTestItem>, uri: String, line: UInt? = null
    ): RobotCodeTestItem? {
        testItems.forEach { item ->
            val found = findTestItem(item, uri, line)
            if (found != null) {
                return found
            }
        }
        
        return null
    }
    
    
    fun findTestItem(element: PsiElement): RobotCodeTestItem? {
        val directory = element as? PsiDirectory
        if (directory != null) {
            return findTestItem(directory.virtualFile.uri)
        }
        
        val containingFile = element.containingFile ?: return null
        if (containingFile !is RobotSuiteFile) {
            return null
        }
        
        if (element is RobotSuiteFile) {
            return findTestItem(containingFile.virtualFile.uri)
        }
        
        if (element.elementType !is IRobotFrameworkElementType) {
            return null
        }
        
        val psiDocumentManager = PsiDocumentManager.getInstance(project) ?: return null
        val document = psiDocumentManager.getDocument(containingFile) ?: return null
        val lineNumber = document.getLineNumber(element.startOffset)
        if (lineNumber <= 0) return null // this is a suite file and this is already caught above
        
        val columnNumber = element.startOffset - document.getLineStartOffset(lineNumber)
        if (columnNumber != 0) return null
        
        val result = findTestItem(containingFile.virtualFile.uri, lineNumber.toUInt())
        return result
    }
}

val VirtualFile.uri: String
    get() {
        return URI.create(fileSystem.protocol + URLUtil.SCHEME_SEPARATOR + "/" + path.replace(":", "%3A")).toString()
    }

val Project.testManger: RobotCodeTestManager
    get() {
        return this.service<RobotCodeTestManager>()
    }
