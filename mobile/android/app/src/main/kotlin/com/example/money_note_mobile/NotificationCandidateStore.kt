package com.example.money_note_mobile

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
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

data class ParsedApproval(
    val cardLast4: String?,
    val entryDate: String?,
    val amount: Int?,
    val merchant: String?
)

data class WooriNotificationLog(
    val id: String,
    val capturedAt: Long,
    val packageName: String,
    val title: String,
    val text: String,
    val bigText: String,
    val rawText: String,
    val isApprovalCandidate: Boolean,
    val parseStatus: String,
    val parseFailureReason: String,
    val parsed: ParsedApproval
)

data class CardNotificationCandidate(
    val id: String,
    val capturedAt: Long,
    val cardLast4: String,
    val cardRole: String,
    val entryDate: String,
    val amount: Int,
    val merchant: String,
    val rawText: String
)

object NotificationCandidateStore {
    private const val PREFS_NAME = "money_note_notification_settings"
    private const val OWNER_CARD_KEY = "owner_card_last4"
    private const val FAMILY_CARD_KEY = "family_card_last4"
    private const val CANDIDATE_FILE_NAME = "card_notification_candidates.json"
    private const val WOORI_LOG_FILE_NAME = "woori_notification_logs.json"
    private const val MAX_WOORI_LOG_COUNT = 30
    private const val CHANNEL_ID = "money_note_card_candidates"
    private const val SUMMARY_NOTIFICATION_ID = 8201

    fun configureCards(context: Context, ownerCardLast4: String, familyCardLast4: String) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(OWNER_CARD_KEY, ownerCardLast4.trim())
            .putString(FAMILY_CARD_KEY, familyCardLast4.trim())
            .apply()
    }

    fun handleNotification(context: Context, record: RawNotificationRecord): HandleResult {
        if (record.packageName != "com.wooricard.smartapp") {
            return HandleResult(
                saved = false,
                candidateCreated = false,
                logCount = logCount(context),
                candidateCount = candidateTotal(context),
                isApprovalCandidate = false,
                parseStatus = "ignored",
                parseFailureReason = "",
                parsed = ParsedApproval(null, null, null, null)
            )
        }

        val parsed = parseApproval(record)
        val role = parsed.approval.cardLast4?.let { cardRole(context, it) }
        val candidate = if (parsed.status == "parsed" && role != null) {
            CardNotificationCandidate(
                id = record.id,
                capturedAt = record.capturedAt,
                cardLast4 = parsed.approval.cardLast4!!,
                cardRole = role,
                entryDate = parsed.approval.entryDate!!,
                amount = parsed.approval.amount!!,
                merchant = parsed.approval.merchant!!,
                rawText = record.rawText
            )
        } else {
            null
        }
        val log = WooriNotificationLog(
            id = record.id,
            capturedAt = record.capturedAt,
            packageName = record.packageName,
            title = record.title,
            text = record.text,
            bigText = record.bigText,
            rawText = record.rawText,
            isApprovalCandidate = parsed.isApprovalCandidate,
            parseStatus = parsed.status,
            parseFailureReason = parsed.reason,
            parsed = parsed.approval
        )

        synchronized(this) {
            val logCount = appendWooriLogLocked(context, log)
            if (candidate != null) appendCandidateLocked(context, candidate)
            updateSummaryNotification(context)
            return HandleResult(
                saved = true,
                candidateCreated = candidate != null,
                logCount = logCount,
                candidateCount = candidateCountLocked(context),
                isApprovalCandidate = parsed.isApprovalCandidate,
                parseStatus = parsed.status,
                parseFailureReason = parsed.reason,
                parsed = parsed.approval
            )
        }
    }

    fun listCandidates(context: Context): String =
        synchronized(this) { readArray(context, CANDIDATE_FILE_NAME).toString() }

    fun listWooriLogs(context: Context): String =
        synchronized(this) { readArray(context, WOORI_LOG_FILE_NAME).toString() }

    fun candidateCounts(context: Context): Map<String, Int> =
        synchronized(this) {
            val counts = candidateCountsLocked(context)
            mapOf("owner" to counts.owner, "family" to counts.family)
        }

    fun manualReviewCount(context: Context): Int =
        synchronized(this) { manualReviewCountLocked(context) }

    fun deleteCandidate(context: Context, id: String): Int =
        deleteMatching(context, CANDIDATE_FILE_NAME) { it.optString("id") == id }
            .also { updateSummaryNotification(context) }

    fun clearCandidatesByRole(context: Context, role: String): Int =
        deleteMatching(context, CANDIDATE_FILE_NAME) { it.optString("card_role") == role }
            .also { updateSummaryNotification(context) }

    fun deleteWooriLog(context: Context, id: String): Int =
        deleteMatching(context, WOORI_LOG_FILE_NAME) { it.optString("id") == id }

    fun clearWooriLogs(context: Context): Int {
        synchronized(this) {
            writeArray(context, WOORI_LOG_FILE_NAME, JSONArray())
            return 0
        }
    }

    fun wooriLogText(context: Context): String {
        synchronized(this) {
            val array = readArray(context, WOORI_LOG_FILE_NAME)
            val lines = mutableListOf("=== Money Note Woori Notification Debug ===", "count: ${array.length()}")
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                lines.add("[${index + 1}]")
                lines.add("capturedAt=${item.optLong("captured_at")}")
                lines.add("parseStatus=${item.optString("parse_status")}")
                lines.add("parseFailureReason=${item.optString("parse_failure_reason")}")
                lines.add("packageName=${item.optString("package_name")}")
                lines.add("title=${item.optString("title")}")
                lines.add("text=${item.optString("text")}")
                lines.add("bigText=${item.optString("big_text")}")
                lines.add("rawText=${item.optString("raw_text")}")
                lines.add("card_last4=${item.optString("card_last4")}")
                lines.add("entry_date=${item.optString("entry_date")}")
                lines.add("amount=${item.optString("amount")}")
                lines.add("merchant=${item.optString("merchant")}")
            }
            return lines.joinToString("\n")
        }
    }

    private fun parseApproval(record: RawNotificationRecord): ParseResult {
        val raw = record.rawText
        val ignored = listOf("(광고)", "이벤트", "혜택", "마케팅", "자동납부", "결제일", "수신거부")
            .any { raw.contains(it) || record.title.contains(it) }
        val approvalCandidate = !ignored && listOf(record.title, record.text, record.bigText, raw).any { it.contains("승인") }
        if (!approvalCandidate) {
            return ParseResult(false, "ignored", "", ParsedApproval(null, null, null, null))
        }
        val base = ParsedApproval(
            cardLast4 = extractCardLast4(raw),
            entryDate = extractEntryDate(raw),
            amount = extractApprovalAmount(raw),
            merchant = extractMerchant(raw)
        )
        if (raw.contains("할부")) {
            return ParseResult(true, "installment_manual", "할부 승인 - 수동 처리 필요", base)
        }
        val missing = mutableListOf<String>()
        if (base.cardLast4 == null) missing.add("card_last4")
        if (base.entryDate == null) missing.add("entry_date")
        if (base.amount == null) missing.add("amount")
        if (base.merchant == null) missing.add("merchant")
        if (missing.isNotEmpty()) {
            return ParseResult(true, "failed", "필수 필드 누락: ${missing.joinToString(", ")}", base)
        }
        return ParseResult(true, "parsed", "", base)
    }

    private fun extractCardLast4(raw: String): String? =
        Regex("""\((\d{4})\)""").find(raw)?.groupValues?.getOrNull(1)

    private fun extractEntryDate(raw: String): String? {
        val match = Regex("""(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)""").find(raw) ?: return null
        val month = match.groupValues[1].toIntOrNull() ?: return null
        val day = match.groupValues[2].toIntOrNull() ?: return null
        val now = java.util.Calendar.getInstance()
        var year = now.get(java.util.Calendar.YEAR)
        if (now.get(java.util.Calendar.MONTH) == java.util.Calendar.JANUARY && month == 12) {
            year -= 1
        }
        return "%04d-%02d-%02d".format(year, month, day)
    }

    private fun extractApprovalAmount(raw: String): Int? {
        for (line in raw.lines()) {
            val target = line.substringBefore("누적")
            val match = Regex("""([0-9][0-9,]*)\s*원""").find(target) ?: continue
            return match.groupValues[1].replace(",", "").toIntOrNull()
        }
        return null
    }

    private fun extractMerchant(raw: String): String? {
        val lines = raw.lines().map { it.trim() }.filter { it.isNotEmpty() }.distinct()
        val ignoredWords = listOf("승인내역", "누적", "승인(", "승인", "원", "수신거부")
        return lines.lastOrNull { line ->
            ignoredWords.none { line.contains(it) } && !Regex("""^\d{1,2}/\d{1,2}""").containsMatchIn(line)
        }
    }

    private fun appendCandidateLocked(context: Context, candidate: CardNotificationCandidate): Int {
        val array = readArray(context, CANDIDATE_FILE_NAME)
        val next = JSONArray()
        next.put(candidate.toJson())
        for (index in 0 until array.length()) {
            val item = array.getJSONObject(index)
            if (item.optString("id") != candidate.id) next.put(item)
        }
        writeArray(context, CANDIDATE_FILE_NAME, next)
        return next.length()
    }

    private fun appendWooriLogLocked(context: Context, log: WooriNotificationLog): Int {
        val array = readArray(context, WOORI_LOG_FILE_NAME)
        val next = JSONArray()
        next.put(log.toJson())
        for (index in 0 until array.length()) {
            val item = array.getJSONObject(index)
            if (item.optString("id") != log.id) next.put(item)
        }
        val trimmed = JSONArray()
        val limit = minOf(next.length(), MAX_WOORI_LOG_COUNT)
        for (index in 0 until limit) trimmed.put(next.getJSONObject(index))
        writeArray(context, WOORI_LOG_FILE_NAME, trimmed)
        return trimmed.length()
    }

    fun updateSummaryNotification(context: Context) {
        synchronized(this) {
            val counts = candidateCountsLocked(context)
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (counts.owner + counts.family == 0) {
                manager.cancel(SUMMARY_NOTIFICATION_ID)
                return
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                manager.createNotificationChannel(
                    NotificationChannel(CHANNEL_ID, "Money-Note 카드 후보", NotificationManager.IMPORTANCE_DEFAULT)
                )
            }
            val description = "본인카드 미확인 ${counts.owner}건\n가족카드 미확인 ${counts.family}건"
            val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Notification.Builder(context, CHANNEL_ID)
            } else {
                @Suppress("DEPRECATION")
                Notification.Builder(context)
            }
            val notification = builder
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("새 내역 발견!")
                .setContentText(description.lines().first())
                .setStyle(Notification.BigTextStyle().bigText(description))
                .setOngoing(false)
                .setAutoCancel(false)
                .build()
            manager.notify(SUMMARY_NOTIFICATION_ID, notification)
        }
    }

    private fun cardRole(context: Context, cardLast4: String): String? {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return when (cardLast4) {
            prefs.getString(OWNER_CARD_KEY, "") -> "owner"
            prefs.getString(FAMILY_CARD_KEY, "") -> "family"
            else -> null
        }
    }

    private fun candidateTotal(context: Context): Int =
        synchronized(this) { candidateCountLocked(context) }

    private fun logCount(context: Context): Int =
        synchronized(this) { readArray(context, WOORI_LOG_FILE_NAME).length() }

    private fun candidateCountLocked(context: Context): Int =
        readArray(context, CANDIDATE_FILE_NAME).length()

    private fun candidateCountsLocked(context: Context): CandidateCounts {
        val array = readArray(context, CANDIDATE_FILE_NAME)
        var owner = 0
        var family = 0
        for (index in 0 until array.length()) {
            when (array.getJSONObject(index).optString("card_role")) {
                "owner" -> owner += 1
                "family" -> family += 1
            }
        }
        return CandidateCounts(owner, family)
    }

    private fun manualReviewCountLocked(context: Context): Int {
        val array = readArray(context, WOORI_LOG_FILE_NAME)
        var count = 0
        for (index in 0 until array.length()) {
            when (array.getJSONObject(index).optString("parse_status")) {
                "failed", "installment_manual" -> count += 1
            }
        }
        return count
    }

    private fun deleteMatching(
        context: Context,
        fileName: String,
        predicate: (JSONObject) -> Boolean
    ): Int {
        synchronized(this) {
            val array = readArray(context, fileName)
            val next = JSONArray()
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                if (!predicate(item)) next.put(item)
            }
            writeArray(context, fileName, next)
            return next.length()
        }
    }

    private fun readArray(context: Context, fileName: String): JSONArray {
        val file = file(context, fileName)
        if (!file.exists()) return JSONArray()
        return try {
            JSONArray(file.readText(Charsets.UTF_8))
        } catch (_: Exception) {
            JSONArray()
        }
    }

    private fun writeArray(context: Context, fileName: String, array: JSONArray) {
        file(context, fileName).writeText(array.toString(), Charsets.UTF_8)
    }

    private fun file(context: Context, fileName: String): File = File(context.filesDir, fileName)

    private fun CardNotificationCandidate.toJson(): JSONObject =
        JSONObject()
            .put("id", id)
            .put("captured_at", capturedAt)
            .put("card_last4", cardLast4)
            .put("card_role", cardRole)
            .put("entry_date", entryDate)
            .put("amount", amount)
            .put("merchant", merchant)
            .put("raw_text", rawText)

    private fun WooriNotificationLog.toJson(): JSONObject =
        JSONObject()
            .put("id", id)
            .put("captured_at", capturedAt)
            .put("package_name", packageName)
            .put("title", title)
            .put("text", text)
            .put("big_text", bigText)
            .put("raw_text", rawText)
            .put("is_approval_candidate", isApprovalCandidate)
            .put("parse_status", parseStatus)
            .put("parse_failure_reason", parseFailureReason)
            .put("card_last4", parsed.cardLast4)
            .put("entry_date", parsed.entryDate)
            .put("amount", parsed.amount)
            .put("merchant", parsed.merchant)
}

data class ParseResult(
    val isApprovalCandidate: Boolean,
    val status: String,
    val reason: String,
    val approval: ParsedApproval
)

data class HandleResult(
    val saved: Boolean,
    val candidateCreated: Boolean,
    val logCount: Int,
    val candidateCount: Int,
    val isApprovalCandidate: Boolean,
    val parseStatus: String,
    val parseFailureReason: String,
    val parsed: ParsedApproval
)

data class CandidateCounts(val owner: Int, val family: Int)
