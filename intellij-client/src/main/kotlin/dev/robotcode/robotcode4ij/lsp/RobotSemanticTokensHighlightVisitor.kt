package dev.robotcode.robotcode4ij.lsp

import com.intellij.codeInsight.daemon.impl.HighlightVisitor
import com.intellij.codeInsight.daemon.impl.analysis.HighlightInfoHolder
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.redhat.devtools.lsp4ij.LSPFileSupport
import com.redhat.devtools.lsp4ij.LSPIJUtils
import com.redhat.devtools.lsp4ij.features.semanticTokens.LazyHighlightInfo
import com.redhat.devtools.lsp4ij.internal.PsiFileChangedException
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import org.eclipse.lsp4j.SemanticTokensParams
import java.util.concurrent.ExecutionException

class RobotSemanticTokensHighlightVisitor : HighlightVisitor {
    override fun suitableForFile(file: PsiFile): Boolean {
        return file.language == RobotFrameworkLanguage
    }
    
    override fun visit(element: PsiElement) {
        // No-op
    }
    
    override fun analyze(
        file: PsiFile,
        updateWholeFile: Boolean,
        holder: HighlightInfoHolder,
        action: Runnable
    ): Boolean {
        action.run()
        runBlocking {
            highlight(file, holder)
        }
        return true
    }
    
    suspend fun highlight(file: PsiFile, holder: HighlightInfoHolder) {
        val semanticTokensSupport = LSPFileSupport.getSupport(file).getSemanticTokensSupport()
        val params = SemanticTokensParams(LSPIJUtils.toTextDocumentIdentifier(file.virtualFile))
        
        val semanticTokens = try {
            semanticTokensSupport.getSemanticTokens(params).await()
        } catch (_: PsiFileChangedException) {
            semanticTokensSupport.cancel()
            return
        } catch (e: ExecutionException) {
            thisLogger().error("Error while consuming LSP 'textDocument/semanticTokens/full' request", e)
            return
        }
        
        val document = LSPIJUtils.getDocument(file.virtualFile) ?: return
        
        semanticTokens.highlight(file, document) { start, end, colorKey ->
            holder.add(LazyHighlightInfo.resolve(start, end, colorKey))
        }
    }
    
    override fun clone(): HighlightVisitor {
        return RobotSemanticTokensHighlightVisitor()
    }
}
