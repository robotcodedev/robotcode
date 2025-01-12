package dev.robotcode.robotcode4ij.utils

import java.net.ServerSocket

object NetUtils {
    fun findFreePort(startPort: Int, endPort: Int? = null): Int {
        
        try {
            ServerSocket(startPort).use { return startPort }
        } catch (_: Exception) {
        
        }
        
        return if (endPort == null) {
            
            ServerSocket(0).use { it.localPort }
        } else {
            (startPort..endPort).firstOrNull { port ->
                try {
                    ServerSocket(port).use { true }
                } catch (e: Exception) {
                    false
                }
            } ?: ServerSocket(0).use { it.localPort }
        }
    }
}
