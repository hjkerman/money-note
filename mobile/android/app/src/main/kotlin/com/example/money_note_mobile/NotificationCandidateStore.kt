package com.example.money_note_mobile

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.AtomicFile
import android.util.Log
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

data class CapturedNotificationLog(
    val id: String,
    val source: String,
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
    val category: String,
    val isApprovalCandidate: Boolean,
    val parseStatus: String,
    val parseFailureReason: String,
    val parsed: ParsedApproval
)

data class CardNotificationCandidate(
    val id: String,
    val eventId: String,
    val source: String,
    val capturedAt: Long,
    val cardLast4: String,
    val cardRole: String,
    val entryDate: String,
    val amount: Int?,
    val merchant: String,
    val usageItem: String,
    val rawText: String
)

object NotificationCandidateStore {
    private const val PREFS_NAME = "money_note_notification_settings"
    private const val OWNER_CARD_KEY = "owner_card_last4"
    private const val FAMILY_CARD_KEY = "family_card_last4"
    private const val CANDIDATE_FILE_NAME = "card_notification_candidates.json"
    private const val PROCESSED_EVENT_FILE_NAME = "processed_notification_events.json"
    private const val MAX_CAPTURED_LOG_COUNT = 30
    private const val CHANNEL_ID = "money_note_card_candidates"
    private const val SUMMARY_NOTIFICATION_ID = 8201

    fun configureCards(context: Context, ownerCardLast4: String, familyCardLast4: String) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(OWNER_CARD_KEY, ownerCardLast4.trim())
            .putString(FAMILY_CARD_KEY, familyCardLast4.trim())
            .apply()
    }

    fun purgeRetiredNotificationLogs(context: Context) {
        NotificationCaptureNotifier.retireHighwayTollSuccessNotifications(context)
        synchronized(this) {
            val activeLogFiles = NotificationSource.entries.map { it.logFileName }.toSet()
            context.filesDir.listFiles()
                ?.filter {
                    it.isFile &&
                        it.name.endsWith("_notification_logs.json") &&
                        it.name !in activeLogFiles
                }
                ?.forEach { it.delete() }
            writeProcessedEventsLocked(
                context,
                readProcessedEventsLocked(context),
                System.currentTimeMillis()
            )
        }
    }

    fun handleNotification(context: Context, record: RawNotificationRecord): HandleResult {
        val source = NotificationSource.fromPackageName(record.packageName)
        if (source == null) {
            return HandleResult(
                saved = false,
                candidateCreated = false,
                logCount = 0,
                candidateCount = candidateTotal(context),
                isApprovalCandidate = false,
                parseStatus = "ignored",
                parseFailureReason = "",
                parsed = ParsedApproval(null, null, null, null)
            )
        }
        val shouldProcess = synchronized(this) {
            shouldProcessEventLocked(context, record)
        }
        if (!shouldProcess) {
            return HandleResult(
                saved = false,
                candidateCreated = false,
                logCount = capturedLogCount(context, source),
                candidateCount = candidateTotal(context),
                isApprovalCandidate = false,
                parseStatus = "duplicate",
                parseFailureReason = "",
                parsed = ParsedApproval(null, null, null, null)
            )
        }
        val result = when (source) {
            NotificationSource.WOORI_CARD -> handleWooriCardNotification(context, record, source)
            NotificationSource.HIGHWAY_TOLL -> handleHighwayTollNotification(context, record, source)
        }
        synchronized(this) {
            completeProcessedEventLocked(context, record, result.candidateId)
        }
        return result
    }

    private fun handleWooriCardNotification(
        context: Context,
        record: RawNotificationRecord,
        source: NotificationSource
    ): HandleResult {
        val parsed = parseApproval(record)
        val role = parsed.approval.cardLast4?.let { cardRole(context, it) }
        val candidate = if (parsed.status == "parsed" && role != null) {
            CardNotificationCandidate(
                id = record.id,
                eventId = record.id,
                source = source.wireName,
                capturedAt = record.capturedAt,
                cardLast4 = parsed.approval.cardLast4!!,
                cardRole = role,
                entryDate = parsed.approval.entryDate!!,
                amount = parsed.approval.amount!!,
                merchant = parsed.approval.merchant!!,
                usageItem = "",
                rawText = record.rawText
            )
        } else {
            null
        }
        val log = capturedLog(
            source = source,
            record = record,
            isApprovalCandidate = parsed.isApprovalCandidate,
            parseStatus = parsed.status,
            parseFailureReason = parsed.reason,
            parsed = parsed.approval
        )

        synchronized(this) {
            val logCount = appendCapturedLogLocked(context, source, log)
            val candidateCreated = candidate?.let { appendCandidateLocked(context, it) } == true
            updateCaptureNotificationsLocked(
                context,
                alertFailure = parsed.status in setOf("failed", "installment_manual")
            )
            return HandleResult(
                saved = true,
                candidateCreated = candidateCreated,
                logCount = logCount,
                candidateCount = candidateCountLocked(context),
                isApprovalCandidate = parsed.isApprovalCandidate,
                parseStatus = parsed.status,
                parseFailureReason = parsed.reason,
                parsed = parsed.approval,
                candidateId = candidate?.id
            )
        }
    }

    private fun handleHighwayTollNotification(
        context: Context,
        record: RawNotificationRecord,
        source: NotificationSource
    ): HandleResult {
        val parsed = HighwayTollNotificationParser.parse(record)
        val parsedApproval = ParsedApproval(
            cardLast4 = null,
            entryDate = parsed.toll.entryDate,
            amount = parsed.toll.amount,
            merchant = parsed.toll.route
        )
        if (!parsed.isTollCandidate) {
            if (record.rawText.isBlank()) {
                return HandleResult(
                    saved = false,
                    candidateCreated = false,
                    logCount = capturedLogCount(context, source),
                    candidateCount = candidateTotal(context),
                    isApprovalCandidate = false,
                    parseStatus = parsed.status,
                    parseFailureReason = parsed.reason,
                    parsed = parsedApproval
                )
            }
            val ignoredLog = capturedLog(
                source = source,
                record = record,
                isApprovalCandidate = false,
                parseStatus = parsed.status,
                parseFailureReason = parsed.reason,
                parsed = parsedApproval
            )
            synchronized(this) {
                val logCount = appendCapturedLogLocked(context, source, ignoredLog)
                updateCaptureNotificationsLocked(context)
                return HandleResult(
                    saved = true,
                    candidateCreated = false,
                    logCount = logCount,
                    candidateCount = candidateCountLocked(context),
                    isApprovalCandidate = false,
                    parseStatus = parsed.status,
                    parseFailureReason = parsed.reason,
                    parsed = parsedApproval
                )
            }
        }
        val candidate = if (parsed.createsCandidate) {
            CardNotificationCandidate(
                id = HighwayTollNotificationParser.semanticCandidateId(parsed.toll),
                eventId = record.id,
                source = source.wireName,
                capturedAt = record.capturedAt,
                cardLast4 = "",
                cardRole = "owner",
                entryDate = parsed.toll.entryDate!!,
                amount = parsed.toll.amount,
                merchant = "통행료",
                usageItem = parsed.toll.route.orEmpty(),
                rawText = record.rawText
            )
        } else {
            null
        }
        val log = capturedLog(
            source = source,
            record = record,
            isApprovalCandidate = parsed.isTollCandidate,
            parseStatus = parsed.status,
            parseFailureReason = parsed.reason,
            parsed = parsedApproval
        )
        synchronized(this) {
            val logCount = appendCapturedLogLocked(context, source, log)
            val candidateCreated = candidate?.let { appendCandidateLocked(context, it) } == true
            updateCaptureNotificationsLocked(
                context,
                alertFailure = requiresManualReview(parsed.status)
            )
            return HandleResult(
                saved = true,
                candidateCreated = candidateCreated,
                logCount = logCount,
                candidateCount = candidateCountLocked(context),
                isApprovalCandidate = parsed.isTollCandidate,
                parseStatus = parsed.status,
                parseFailureReason = parsed.reason,
                parsed = parsedApproval,
                candidateId = candidate?.id
            )
        }
    }

    private fun capturedLog(
        source: NotificationSource,
        record: RawNotificationRecord,
        isApprovalCandidate: Boolean,
        parseStatus: String,
        parseFailureReason: String,
        parsed: ParsedApproval
    ): CapturedNotificationLog =
        CapturedNotificationLog(
            id = record.id,
            source = source.wireName,
            capturedAt = record.capturedAt,
            packageName = record.packageName,
            title = record.title,
            text = record.text,
            bigText = record.bigText,
            subText = record.subText,
            textLines = record.textLines,
            rawText = record.rawText,
            notificationKey = record.notificationKey,
            postTime = record.postTime,
            isOngoing = record.isOngoing,
            category = record.category,
            isApprovalCandidate = isApprovalCandidate,
            parseStatus = parseStatus,
            parseFailureReason = parseFailureReason,
            parsed = parsed
        )

    fun listCandidates(context: Context): String =
        synchronized(this) { readArray(context, CANDIDATE_FILE_NAME).toString() }

    fun listCapturedLogs(context: Context, sourceName: String): String =
        synchronized(this) {
            val source = NotificationSource.fromWireName(sourceName) ?: return@synchronized "[]"
            readArray(context, source.logFileName).toString()
        }

    fun candidateCounts(context: Context): Map<String, Int> =
        synchronized(this) {
            val counts = candidateCountsLocked(context)
            mapOf("owner" to counts.owner, "family" to counts.family)
        }

    fun manualReviewCount(context: Context): Int =
        synchronized(this) { manualReviewCountLocked(context) }

    fun deleteCandidate(context: Context, id: String): Int = synchronized(this) {
        val candidates = readArray(context, CANDIDATE_FILE_NAME)
        val removed = (0 until candidates.length())
            .map { candidates.getJSONObject(it) }
            .firstOrNull { it.optString("id") == id }
        val count = deleteMatchingLocked(CANDIDATE_FILE_NAME, context) {
            it.optString("id") == id
        }
        markCandidatesConsumedLocked(context, listOfNotNull(removed))
        updateCaptureNotificationsLocked(context)
        count
    }

    fun clearCandidatesByRole(context: Context, role: String): Int = synchronized(this) {
        val candidates = readArray(context, CANDIDATE_FILE_NAME)
        val removedCandidates = (0 until candidates.length())
            .map { candidates.getJSONObject(it) }
            .filter { it.optString("card_role") == role }
        val count = deleteMatchingLocked(CANDIDATE_FILE_NAME, context) {
            it.optString("card_role") == role
        }
        markCandidatesConsumedLocked(context, removedCandidates)
        updateCaptureNotificationsLocked(context)
        count
    }

    fun deleteCapturedLog(context: Context, sourceName: String, id: String): Int {
        val source = NotificationSource.fromWireName(sourceName) ?: return 0
        synchronized(this) {
            val count = deleteMatchingLocked(source.logFileName, context) { it.optString("id") == id }
            updateFailureNotificationLocked(context)
            return count
        }
    }

    fun clearCapturedLogs(context: Context, sourceName: String): Int {
        val source = NotificationSource.fromWireName(sourceName) ?: return 0
        synchronized(this) {
            writeArray(context, source.logFileName, JSONArray())
            updateFailureNotificationLocked(context)
            return 0
        }
    }

    fun capturedLogText(context: Context, sourceName: String): String {
        val source = NotificationSource.fromWireName(sourceName) ?: return ""
        synchronized(this) {
            val array = readArray(context, source.logFileName)
            val lines = mutableListOf(
                "=== Money Note ${source.debugTitle} Notification Debug ===",
                "count: ${array.length()}"
            )
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                lines.add("[${index + 1}]")
                lines.add("source=${item.optString("source", source.wireName)}")
                lines.add("capturedAt=${item.optLong("captured_at")}")
                lines.add("parseStatus=${item.optString("parse_status")}")
                lines.add("parseFailureReason=${item.optString("parse_failure_reason")}")
                lines.add("packageName=${item.optString("package_name")}")
                lines.add("title=${item.optString("title")}")
                lines.add("text=${item.optString("text")}")
                lines.add("bigText=${item.optString("big_text")}")
                lines.add("subText=${item.optString("sub_text")}")
                lines.add("textLines=${item.optJSONArray("text_lines") ?: JSONArray()}")
                lines.add("rawText=${item.optString("raw_text")}")
                lines.add("notificationKey=${item.optString("notification_key")}")
                lines.add("postTime=${item.optLong("post_time")}")
                lines.add("isOngoing=${item.optBoolean("is_ongoing")}")
                lines.add("category=${item.optString("category")}")
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
        val approvalCandidate = isApprovalNotificationCandidate(
            record.title,
            record.text,
            record.bigText,
            raw
        )
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

    internal fun isApprovalNotificationCandidate(title: String, text: String, bigText: String, raw: String): Boolean {
        val ignoredTerms = listOf(
            "(광고)",
            "이벤트",
            "혜택",
            "마케팅",
            "자동납부",
            "결제일",
            "수신거부",
            "취소",
            "승인취소",
            "매출취소"
        )
        val bodies = listOf(title, text, bigText, raw)
        if (ignoredTerms.any { term -> bodies.any { it.contains(term) } }) return false
        return bodies.any { it.contains("승인") }
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

    internal fun extractMerchant(raw: String): String? {
        val lines = raw.lines().map { it.trim() }.filter { it.isNotEmpty() }.distinct()
        return lines.lastOrNull { line -> !isApprovalMetadataLine(line) }
    }

    private fun isApprovalMetadataLine(line: String): Boolean {
        if (line == "승인내역" || line.contains("누적") || line.contains("수신거부")) return true
        if (Regex("""\[[^\]]*승인\(\d{4}\)\]""").containsMatchIn(line)) return true
        if (Regex("""^\d{1,2}/\d{1,2}(?:\s+\d{1,2}:\d{2})?$""").matches(line)) return true
        return Regex("""^[0-9][0-9,]*\s*원(?:\s*/.*)?$""").matches(line)
    }

    private fun appendCandidateLocked(context: Context, candidate: CardNotificationCandidate): Boolean {
        val array = readArray(context, CANDIDATE_FILE_NAME)
        val existed = (0 until array.length())
            .any { array.getJSONObject(it).optString("id") == candidate.id }
        val next = JSONArray()
        next.put(candidate.toJson())
        for (index in 0 until array.length()) {
            val existing = array.getJSONObject(index)
            if (existing.optString("id") != candidate.id) next.put(existing)
        }
        writeArray(context, CANDIDATE_FILE_NAME, next)
        return !existed
    }

    private fun appendCapturedLogLocked(
        context: Context,
        source: NotificationSource,
        log: CapturedNotificationLog
    ): Int {
        val array = readArray(context, source.logFileName)
        val next = JSONArray()
        next.put(log.toJson())
        for (index in 0 until array.length()) {
            val item = array.getJSONObject(index)
            if (item.optString("id") != log.id) next.put(item)
        }
        val trimmed = JSONArray()
        val limit = minOf(next.length(), MAX_CAPTURED_LOG_COUNT)
        for (index in 0 until limit) trimmed.put(next.getJSONObject(index))
        writeArray(context, source.logFileName, trimmed)
        return trimmed.length()
    }

    private fun updateSummaryNotificationLocked(context: Context) {
        val counts = notificationSummaryCounts(
            cardCounts = candidateCountsLocked(context, NotificationSource.WOORI_CARD.wireName),
            tollCounts = candidateCountsLocked(context, NotificationSource.HIGHWAY_TOLL.wireName)
        )
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (counts.owner + counts.family == 0) {
            manager.cancel(SUMMARY_NOTIFICATION_ID)
            return
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "Money-Note 카드 후보",
                    NotificationManager.IMPORTANCE_DEFAULT
                )
            )
        }
        val description = "본인카드 미확인 ${counts.owner}건\n가족카드 미확인 ${counts.family}건"
        val openIntent = Intent(context, MainActivity::class.java)
            .setAction(MainActivity.ACTION_OPEN_NOTIFICATION_IMPORT)
            .putExtra(MainActivity.EXTRA_OPEN_NOTIFICATION_IMPORT, true)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        val pendingIntent = PendingIntent.getActivity(
            context,
            SUMMARY_NOTIFICATION_ID,
            openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
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
            .setContentIntent(pendingIntent)
            .setOngoing(false)
            .setAutoCancel(false)
            .build()
        manager.notify(SUMMARY_NOTIFICATION_ID, notification)
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

    private fun candidateCountLocked(context: Context): Int =
        readArray(context, CANDIDATE_FILE_NAME).length()

    private fun candidateCountsLocked(context: Context, source: String? = null): CandidateCounts {
        val array = readArray(context, CANDIDATE_FILE_NAME)
        var owner = 0
        var family = 0
        for (index in 0 until array.length()) {
            val item = array.getJSONObject(index)
            val itemSource = item.optString("source", NotificationSource.WOORI_CARD.wireName)
            if (source != null && itemSource != source) continue
            when (item.optString("card_role")) {
                "owner" -> owner += 1
                "family" -> family += 1
            }
        }
        return CandidateCounts(owner, family)
    }

    private fun manualReviewCountLocked(context: Context): Int {
        var count = 0
        val pendingEventIds = pendingCandidateEventIdsLocked(context)
        for (source in NotificationSource.entries) {
            val array = readArray(context, source.logFileName)
            for (index in 0 until array.length()) {
                if (requiresManualReview(array.getJSONObject(index), pendingEventIds)) {
                    count += 1
                }
            }
        }
        return count
    }

    private fun capturedLogCount(context: Context, source: NotificationSource): Int =
        synchronized(this) { readArray(context, source.logFileName).length() }

    private fun updateCaptureNotificationsLocked(
        context: Context,
        alertFailure: Boolean = false
    ) {
        NotificationCaptureNotifier.retireHighwayTollSuccessNotifications(context)
        updateSummaryNotificationLocked(context)
        updateFailureNotificationLocked(context, alert = alertFailure)
    }

    private fun updateFailureNotificationLocked(context: Context, alert: Boolean = false) {
        val failures = mutableListOf<CapturedNotificationLog>()
        val pendingEventIds = pendingCandidateEventIdsLocked(context)
        for (source in NotificationSource.entries) {
            val array = readArray(context, source.logFileName)
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                if (!requiresManualReview(item, pendingEventIds)) continue
                failures.add(item.toCapturedLog(source))
            }
        }
        NotificationCaptureNotifier.updateFailureSummary(context, failures, alert)
    }

    private fun pendingCandidateEventIdsLocked(context: Context): Set<String> {
        val candidates = readArray(context, CANDIDATE_FILE_NAME)
        return (0 until candidates.length())
            .map { candidates.getJSONObject(it) }
            .map { it.optString("event_id").ifEmpty { it.optString("id") } }
            .filter(String::isNotEmpty)
            .toSet()
    }

    private fun requiresManualReview(
        item: JSONObject,
        pendingEventIds: Set<String>
    ): Boolean = requiresManualReview(
        status = item.optString("parse_status"),
        eventId = item.optString("id"),
        pendingEventIds = pendingEventIds
    )

    private fun deleteMatchingLocked(
        fileName: String,
        context: Context,
        predicate: (JSONObject) -> Boolean
    ): Int {
        val array = readArray(context, fileName)
        val next = JSONArray()
        for (index in 0 until array.length()) {
            val item = array.getJSONObject(index)
            if (!predicate(item)) next.put(item)
        }
        writeArray(context, fileName, next)
        return next.length()
    }

    private fun shouldProcessEventLocked(
        context: Context,
        record: RawNotificationRecord
    ): Boolean {
        val now = record.capturedAt
        val events = readProcessedEventsLocked(context)
        val eventId = NotificationEventPolicy.eventId(
            record.packageName,
            record.notificationKey,
            record.postTime
        )
        val contentHash = NotificationEventPolicy.contentHash(record.rawText)
        val existing = events.firstOrNull { it.eventId == eventId }
            ?: return true
        val refreshed = existing.copy(lastSeenAt = now)
        writeProcessedEventsLocked(
            context,
            events.map { if (it.eventId == eventId) refreshed else it },
            now
        )
        if (existing.state == NotificationEventPolicy.STATE_CONSUMED) return false
        return existing.contentHash != contentHash
    }

    private fun completeProcessedEventLocked(
        context: Context,
        record: RawNotificationRecord,
        candidateId: String?
    ) {
        val now = record.capturedAt
        val eventId = NotificationEventPolicy.eventId(
            record.packageName,
            record.notificationKey,
            record.postTime
        )
        val contentHash = NotificationEventPolicy.contentHash(record.rawText)
        val events = readProcessedEventsLocked(context)
        val existing = events.firstOrNull { it.eventId == eventId }
        val completed = ProcessedNotificationEvent(
            eventId = eventId,
            contentHash = contentHash,
            lastSeenAt = now,
            state = if (candidateId != null) {
                NotificationEventPolicy.STATE_PENDING
            } else {
                existing?.state ?: NotificationEventPolicy.STATE_OBSERVED
            },
            candidateId = candidateId ?: existing?.candidateId
        )
        writeProcessedEventsLocked(
            context,
            events.filterNot { it.eventId == eventId } + completed,
            now
        )
    }

    private fun markCandidatesConsumedLocked(
        context: Context,
        candidates: List<JSONObject>
    ) {
        if (candidates.isEmpty()) return
        val now = System.currentTimeMillis()
        val candidateIds = candidates.map { it.optString("id") }.filter { it.isNotEmpty() }.toSet()
        val explicitEventIds = candidates
            .map { it.optString("event_id") }
            .filter { it.isNotEmpty() }
            .toSet()
        val events = readProcessedEventsLocked(context).toMutableList()
        val matchedEventIds = mutableSetOf<String>()
        for (index in events.indices) {
            val event = events[index]
            if (event.eventId !in explicitEventIds && event.candidateId !in candidateIds) continue
            events[index] = event.copy(
                lastSeenAt = now,
                state = NotificationEventPolicy.STATE_CONSUMED
            )
            matchedEventIds.add(event.eventId)
        }
        for (eventId in explicitEventIds - matchedEventIds) {
            val candidateId = candidates.firstOrNull {
                it.optString("event_id") == eventId
            }?.optString("id")
            events.add(
                ProcessedNotificationEvent(
                    eventId = eventId,
                    contentHash = "",
                    lastSeenAt = now,
                    state = NotificationEventPolicy.STATE_CONSUMED,
                    candidateId = candidateId
                )
            )
        }
        writeProcessedEventsLocked(context, events, now)
    }

    private fun readProcessedEventsLocked(context: Context): List<ProcessedNotificationEvent> {
        val processedFile = file(context, PROCESSED_EVENT_FILE_NAME)
        if (processedFile.exists() || File("${processedFile.path}.bak").exists()) {
            val array = readArray(context, PROCESSED_EVENT_FILE_NAME)
            return (0 until array.length()).map { array.getJSONObject(it).toProcessedEvent() }
        }

        val candidateIds = readArray(context, CANDIDATE_FILE_NAME)
            .let { array -> (0 until array.length()).map { array.getJSONObject(it).optString("id") }.toSet() }
        val seeded = mutableListOf<ProcessedNotificationEvent>()
        for (source in NotificationSource.entries) {
            val logs = readArray(context, source.logFileName)
            for (index in 0 until logs.length()) {
                val log = logs.getJSONObject(index)
                val packageName = log.optString("package_name")
                val notificationKey = log.optString("notification_key")
                val postTime = log.optLong("post_time")
                if (packageName.isEmpty() || notificationKey.isEmpty() || postTime <= 0L) continue
                val logId = log.optString("id")
                val candidateId = logId.takeIf { it in candidateIds }
                seeded.add(
                    ProcessedNotificationEvent(
                        eventId = NotificationEventPolicy.eventId(
                            packageName,
                            notificationKey,
                            postTime
                        ),
                        contentHash = NotificationEventPolicy.contentHash(log.optString("raw_text")),
                        lastSeenAt = log.optLong("captured_at"),
                        state = if (candidateId != null) {
                            NotificationEventPolicy.STATE_PENDING
                        } else {
                            NotificationEventPolicy.STATE_OBSERVED
                        },
                        candidateId = candidateId
                    )
                )
            }
        }
        writeProcessedEventsLocked(context, seeded, System.currentTimeMillis())
        return NotificationEventPolicy.prune(seeded, System.currentTimeMillis())
    }

    private fun writeProcessedEventsLocked(
        context: Context,
        events: List<ProcessedNotificationEvent>,
        now: Long
    ) {
        val array = JSONArray()
        NotificationEventPolicy.prune(events, now).forEach { array.put(it.toJson()) }
        writeArray(context, PROCESSED_EVENT_FILE_NAME, array)
    }

    private fun readArray(context: Context, fileName: String): JSONArray {
        val file = file(context, fileName)
        if (!file.exists() && !File("${file.path}.bak").exists()) return JSONArray()
        return try {
            val text = AtomicFile(file).openRead().bufferedReader(Charsets.UTF_8).use { it.readText() }
            JSONArray(text)
        } catch (error: Exception) {
            Log.e("MN_NOTIFY", "failed to read local notification data: $fileName", error)
            JSONArray()
        }
    }

    private fun writeArray(context: Context, fileName: String, array: JSONArray) {
        val atomicFile = AtomicFile(file(context, fileName))
        val output = atomicFile.startWrite()
        try {
            output.write(array.toString().toByteArray(Charsets.UTF_8))
            output.flush()
            atomicFile.finishWrite(output)
        } catch (error: Exception) {
            atomicFile.failWrite(output)
            throw error
        }
    }

    private fun file(context: Context, fileName: String): File = File(context.filesDir, fileName)

    private fun CardNotificationCandidate.toJson(): JSONObject =
        JSONObject()
            .put("id", id)
            .put("event_id", eventId)
            .put("source", source)
            .put("captured_at", capturedAt)
            .put("card_last4", cardLast4)
            .put("card_role", cardRole)
            .put("entry_date", entryDate)
            .put("amount", amount ?: JSONObject.NULL)
            .put("merchant", merchant)
            .put("usage_item", usageItem)
            .put("raw_text", rawText)

    private fun CapturedNotificationLog.toJson(): JSONObject =
        JSONObject()
            .put("id", id)
            .put("source", source)
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
            .put("is_approval_candidate", isApprovalCandidate)
            .put("parse_status", parseStatus)
            .put("parse_failure_reason", parseFailureReason)
            .put("card_last4", parsed.cardLast4)
            .put("entry_date", parsed.entryDate)
            .put("amount", parsed.amount)
            .put("merchant", parsed.merchant)

    private fun ProcessedNotificationEvent.toJson(): JSONObject =
        JSONObject()
            .put("event_id", eventId)
            .put("content_hash", contentHash)
            .put("last_seen_at", lastSeenAt)
            .put("state", state)
            .put("candidate_id", candidateId)

    private fun JSONObject.toProcessedEvent(): ProcessedNotificationEvent =
        ProcessedNotificationEvent(
            eventId = optString("event_id"),
            contentHash = optString("content_hash"),
            lastSeenAt = optLong("last_seen_at"),
            state = optString("state", NotificationEventPolicy.STATE_OBSERVED),
            candidateId = optString("candidate_id").ifEmpty { null }
        )

    private fun JSONObject.toCapturedLog(source: NotificationSource): CapturedNotificationLog =
        CapturedNotificationLog(
            id = optString("id"),
            source = optString("source", source.wireName),
            capturedAt = optLong("captured_at"),
            packageName = optString("package_name"),
            title = optString("title"),
            text = optString("text"),
            bigText = optString("big_text"),
            subText = optString("sub_text"),
            textLines = optJSONArray("text_lines")?.let { array ->
                (0 until array.length()).map { array.optString(it) }
            }.orEmpty(),
            rawText = optString("raw_text"),
            notificationKey = optString("notification_key"),
            postTime = optLong("post_time"),
            isOngoing = optBoolean("is_ongoing"),
            category = optString("category"),
            isApprovalCandidate = optBoolean("is_approval_candidate"),
            parseStatus = optString("parse_status"),
            parseFailureReason = optString("parse_failure_reason"),
            parsed = ParsedApproval(
                cardLast4 = optString("card_last4").ifEmpty { null },
                entryDate = optString("entry_date").ifEmpty { null },
                amount = if (has("amount") && !isNull("amount")) optInt("amount") else null,
                merchant = optString("merchant").ifEmpty { null }
            )
        )
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
    val parsed: ParsedApproval,
    val candidateId: String? = null
)

data class CandidateCounts(val owner: Int, val family: Int)

internal fun notificationSummaryCounts(
    cardCounts: CandidateCounts,
    tollCounts: CandidateCounts
): CandidateCounts = CandidateCounts(
    owner = cardCounts.owner + tollCounts.owner + tollCounts.family,
    family = cardCounts.family
)

internal fun requiresManualReview(status: String): Boolean =
    status in setOf("failed", "installment_manual", "partial")

internal fun requiresManualReview(
    status: String,
    eventId: String,
    pendingEventIds: Set<String>
): Boolean = requiresManualReview(status) &&
    (status != "partial" || eventId in pendingEventIds)
