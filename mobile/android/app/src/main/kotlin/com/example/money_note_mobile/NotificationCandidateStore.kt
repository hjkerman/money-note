package com.example.money_note_mobile

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

data class RawNotificationRecord(
    val id: String,
    val capturedAt: Long,
    val packageName: String,
    val title: String,
    val text: String,
    val bigText: String,
    val subText: String,
    val textLines: List<String>,
    val rawText: String,
    val notificationKey: String,
    val postTime: Long,
    val isOngoing: Boolean,
    val category: String
)

object NotificationCandidateStore {
    private const val RAW_FILE_NAME = "raw_notification_archive.json"
    private const val MAX_RAW_COUNT = 100

    fun appendRaw(context: Context, record: RawNotificationRecord): Int {
        synchronized(this) {
            val array = readArray(context)
            val next = JSONArray()
            next.put(record.toJson())
            for (index in 0 until array.length()) {
                next.put(array.getJSONObject(index))
            }
            val trimmed = JSONArray()
            val limit = minOf(next.length(), MAX_RAW_COUNT)
            for (index in 0 until limit) {
                trimmed.put(next.getJSONObject(index))
            }
            writeArray(context, trimmed)
            return trimmed.length()
        }
    }

    fun listRaw(context: Context): String {
        synchronized(this) {
            return readArray(context).toString()
        }
    }

    fun logText(context: Context): String {
        synchronized(this) {
            val array = readArray(context)
            val lines = mutableListOf<String>()
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                lines.add("capturedAt=${item.optLong("captured_at")}")
                lines.add("packageName=${item.optString("package_name")}")
                lines.add("title=${item.optString("title")}")
                lines.add("text=${item.optString("text")}")
                lines.add("bigText=${item.optString("big_text")}")
                lines.add("rawText=${item.optString("raw_text")}")
                lines.add("---")
            }
            return lines.joinToString("\n")
        }
    }

    private fun readArray(context: Context): JSONArray {
        val file = file(context)
        if (!file.exists()) return JSONArray()
        return try {
            JSONArray(file.readText(Charsets.UTF_8))
        } catch (_: Exception) {
            JSONArray()
        }
    }

    private fun writeArray(context: Context, array: JSONArray) {
        file(context).writeText(array.toString(), Charsets.UTF_8)
    }

    private fun file(context: Context): File = File(context.filesDir, RAW_FILE_NAME)

    private fun RawNotificationRecord.toJson(): JSONObject =
        JSONObject()
            .put("id", id)
            .put("captured_at", capturedAt)
            .put("package_name", packageName)
            .put("title", title)
            .put("text", text)
            .put("big_text", bigText)
            .put("sub_text", subText)
            .put("text_lines", JSONArray(textLines))
            .put("raw_text", rawText)
            .put("notification_key", notificationKey)
            .put("post_time", postTime)
            .put("is_ongoing", isOngoing)
            .put("category", category)
}
