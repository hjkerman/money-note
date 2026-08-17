package com.example.money_note_mobile

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Intent
import androidx.core.content.FileProvider
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodChannel
import java.io.File

class ChatGptShareBridge(
    private val activity: Activity,
    messenger: BinaryMessenger,
) {
    companion object {
        private const val CHANNEL_NAME = "money_note/chatgpt_share"
        private const val CHATGPT_PACKAGE = "com.openai.chatgpt"
        private const val REPORT_DIRECTORY = "ai-audit"
        private val SAFE_FILENAME = Regex("[^A-Za-z0-9._-]")
    }

    private val channel = MethodChannel(messenger, CHANNEL_NAME)
    private var sharedReport: File? = null
    private var waitingForReturn = false

    init {
        cleanupReports()
        channel.setMethodCallHandler { call, result ->
            when (call.method) {
                "shareAudit" -> shareAudit(
                    filename = call.argument<String>("filename").orEmpty(),
                    markdown = call.argument<String>("markdown").orEmpty(),
                    result = result,
                )
                else -> result.notImplemented()
            }
        }
    }

    fun dispose() {
        channel.setMethodCallHandler(null)
    }

    fun onHostResumed() {
        if (!waitingForReturn) return
        sharedReport?.delete()
        sharedReport = null
        waitingForReturn = false
    }

    private fun shareAudit(
        filename: String,
        markdown: String,
        result: MethodChannel.Result,
    ) {
        if (markdown.isBlank()) {
            result.error("empty_report", "회계감사 자료가 비어 있습니다.", null)
            return
        }
        cleanupReports()
        val directory = File(activity.cacheDir, REPORT_DIRECTORY).apply { mkdirs() }
        val report = File(directory, safeFilename(filename)).apply {
            writeText(markdown, Charsets.UTF_8)
        }
        val authority = "${activity.packageName}.shared_files"
        val uri = FileProvider.getUriForFile(activity, authority, report)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            setPackage(CHATGPT_PACKAGE)
            putExtra(Intent.EXTRA_STREAM, uri)
            clipData = ClipData.newUri(activity.contentResolver, report.name, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            activity.grantUriPermission(
                CHATGPT_PACKAGE,
                uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION,
            )
            sharedReport = report
            waitingForReturn = true
            activity.startActivity(intent)
            result.success(true)
        } catch (_: ActivityNotFoundException) {
            report.delete()
            sharedReport = null
            waitingForReturn = false
            result.error("chatgpt_not_installed", "ChatGPT 앱을 찾을 수 없습니다.", null)
        } catch (error: Exception) {
            report.delete()
            sharedReport = null
            waitingForReturn = false
            result.error("share_failed", error.message ?: "ChatGPT 앱을 열 수 없습니다.", null)
        }
    }

    private fun cleanupReports() {
        File(activity.cacheDir, REPORT_DIRECTORY).listFiles()?.forEach(File::delete)
    }

    private fun safeFilename(filename: String): String {
        val cleaned = filename
            .ifBlank { "money-note-audit.md" }
            .replace(SAFE_FILENAME, "_")
            .take(120)
        return if (cleaned.endsWith(".md", ignoreCase = true)) cleaned else "$cleaned.md"
    }
}
