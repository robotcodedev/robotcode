package dev.robotcode.robotcode4ij.debugging

import com.intellij.openapi.diagnostic.thisLogger
import com.jetbrains.rd.util.reactive.Signal
import org.eclipse.lsp4j.debug.OutputEventArguments
import org.eclipse.lsp4j.debug.StoppedEventArguments
import org.eclipse.lsp4j.debug.TerminatedEventArguments
import org.eclipse.lsp4j.debug.services.IDebugProtocolClient
import org.eclipse.lsp4j.jsonrpc.services.JsonNotification

data class RobotEnqueuedArguments(var items: Array<String>) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        
        other as RobotEnqueuedArguments
        
        return items.contentEquals(other.items)
    }
    
    override fun hashCode(): Int {
        return items.contentHashCode()
    }
}

data class RobotExitedEventArguments(
    var reportFile: String? = null,
    var logFile: String? = null,
    var outputFile: String? = null,
    var exitCode: Int? = null
)

data class RobotExecutionAttributes(
    var id: String? = null,
    var parentId: String? = null,
    var longname: String? = null,
    var template: String? = null,
    var status: String? = null,
    var message: String? = null,
    var elapsedtime: Int? = null,
    var source: String? = null,
    var lineno: Int? = null,
    var starttime: String? = null,
    var endtime: String? = null,
    var tags: Array<String>? = null,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        
        other as RobotExecutionAttributes
        
        if (elapsedtime != other.elapsedtime) return false
        if (lineno != other.lineno) return false
        if (id != other.id) return false
        if (parentId != other.parentId) return false
        if (longname != other.longname) return false
        if (template != other.template) return false
        if (status != other.status) return false
        if (message != other.message) return false
        if (source != other.source) return false
        if (starttime != other.starttime) return false
        if (endtime != other.endtime) return false
        if (tags != null) {
            if (other.tags == null) return false
            if (!tags.contentEquals(other.tags)) return false
        } else if (other.tags != null) return false
        
        return true
    }
    
    override fun hashCode(): Int {
        var result = elapsedtime?.hashCode() ?: 0
        result = 31 * result + (lineno ?: 0)
        result = 31 * result + (id?.hashCode() ?: 0)
        result = 31 * result + (parentId?.hashCode() ?: 0)
        result = 31 * result + (longname?.hashCode() ?: 0)
        result = 31 * result + (template?.hashCode() ?: 0)
        result = 31 * result + (status?.hashCode() ?: 0)
        result = 31 * result + (message?.hashCode() ?: 0)
        result = 31 * result + (source?.hashCode() ?: 0)
        result = 31 * result + (starttime?.hashCode() ?: 0)
        result = 31 * result + (endtime?.hashCode() ?: 0)
        result = 31 * result + (tags?.contentHashCode() ?: 0)
        return result
    }
}

data class RobotExecutionEventArguments(
    var type: String,
    var id: String,
    var name: String,
    var parentId: String? = null,
    var attributes: RobotExecutionAttributes,
    var failedKeywords: Array<RobotExecutionAttributes>? = null,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        
        other as RobotExecutionEventArguments
        
        if (type != other.type) return false
        if (id != other.id) return false
        if (attributes != other.attributes) return false
        if (failedKeywords != null) {
            if (other.failedKeywords == null) return false
            if (!failedKeywords.contentEquals(other.failedKeywords)) return false
        } else if (other.failedKeywords != null) return false
        
        return true
    }
    
    override fun hashCode(): Int {
        var result = type.hashCode()
        result = 31 * result + id.hashCode()
        result = 31 * result + attributes.hashCode()
        result = 31 * result + (failedKeywords?.contentHashCode() ?: 0)
        return result
    }
}

enum class RobotLogLevel {
    FAIL,
    ERROR,
    WARN,
    INFO,
    DEBUG,
    TRACE
}

data class RobotLogMessageEventArguments(
    var itemId: String? = null,
    var source: String? = null,
    var lineno: Int? = null,
    var column: Int? = null,
    var message: String? = null,
    var level: String? = null,
    var timestamp: String? = null,
    var html: String? = null
)

@Suppress("unused") class RobotCodeDebugProtocolClient : IDebugProtocolClient {
    var onStopped = Signal<StoppedEventArguments>()
    val onTerminated = Signal<TerminatedEventArguments?>()
    
    val onRobotEnqueued = Signal<RobotEnqueuedArguments>()
    val onRobotStarted = Signal<RobotExecutionEventArguments>()
    val onRobotEnded = Signal<RobotExecutionEventArguments>()
    val onRobotSetFailed = Signal<RobotExecutionEventArguments>()
    val onRobotExited = Signal<RobotExitedEventArguments>()
    val onRobotLog = Signal<RobotLogMessageEventArguments>()
    val onRobotMessage = Signal<RobotLogMessageEventArguments>()
    val onOutput = Signal<OutputEventArguments>()
    
    override fun terminated(args: TerminatedEventArguments?) {
        super.terminated(args)
        onTerminated.fire(args)
    }
    
    override fun stopped(args: StoppedEventArguments) {
        super.stopped(args)
        onStopped.fire(args)
    }
    
    @JsonNotification("robotEnqueued") fun robotEnqueued(args: RobotEnqueuedArguments) {
        thisLogger().trace("robotEnqueued")
        onRobotEnqueued.fire(args)
    }
    
    @JsonNotification("robotStarted") fun robotStarted(args: RobotExecutionEventArguments) {
        thisLogger().trace("robotStarted $args")
        onRobotStarted.fire(args)
    }
    
    @JsonNotification("robotEnded") fun robotEnded(args: RobotExecutionEventArguments) {
        thisLogger().trace("robotEnded $args")
        onRobotEnded.fire(args)
    }
    
    @JsonNotification("robotSetFailed") fun robotSetFailed(args: RobotExecutionEventArguments) {
        thisLogger().trace("robotSetFailed $args")
        onRobotSetFailed.fire(args)
    }
    
    @JsonNotification("robotExited") fun robotExited(args: RobotExitedEventArguments) {
        thisLogger().trace("robotExited")
        onRobotExited.fire(args)
    }
    
    @JsonNotification("robotLog") fun robotLog(args: RobotLogMessageEventArguments) {
        thisLogger().trace("robotLog")
        onRobotLog.fire(args)
    }
    
    @JsonNotification("robotMessage") fun robotMessage(args: RobotLogMessageEventArguments) {
        thisLogger().trace("robotMessage")
        onRobotMessage.fire(args)
    }
    
    override fun output(args: OutputEventArguments) {
        super.output(args)
        onOutput.fire(args)
    }
    
}
