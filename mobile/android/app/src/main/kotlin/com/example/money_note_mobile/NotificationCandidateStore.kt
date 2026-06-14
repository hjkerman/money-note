package com.example.money_note_mobile

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

data class NotificationCandidate(
    val id: String,
    val capturedAt: Long,
    val cardLast4: String,
    val monthDay: String,
    val time: String,
    val amount: Int,
    val usagePlace: String
)

object NotificationCandidateStore {
    private const val FILE_NAME = "pending_card_notifications.json"

    fun append(context: Context, candidate: NotificationCandidate): Boolean {
        synchronized(this) {
            val array = readArray(context)
            if (contains(array, candidate.id)) return false
            array.put(candidate.toJson())
            writeArray(context, array)
            return true
        }
    }

    fun list(context: Context): String {
        synchronized(this) {
            return readArray(context).toString()
        }
    }

    fun delete(context: Context, id: String): Boolean {
        synchronized(this) {
            val original = readArray(context)
            val next = JSONArray()
            var deleted = false
            for (index in 0 until original.length()) {
                val item = original.getJSONObject(index)
                if (item.optString("id") == id) {
                    deleted = true
                } else {
                    next.put(item)
                }
            }
            if (deleted) writeArray(context, next)
            return deleted
        }
    }

    private fun contains(array: JSONArray, id: String): Boolean {
        for (index in 0 until array.length()) {
            if (array.getJSONObject(index).optString("id") == id) return true
        }
        return false
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

    private fun file(context: Context): File = File(context.filesDir, FILE_NAME)

    private fun NotificationCandidate.toJson(): JSONObject =
        JSONObject()
            .put("id", id)
            .put("captured_at", capturedAt)
            .put("card_last4", cardLast4)
            .put("month_day", monthDay)
            .put("time", time)
            .put("amount", amount)
            .put("usage_place", usagePlace)
}
