package com.example.money_note_mobile

import java.security.MessageDigest

data class ProcessedNotificationEvent(
    val eventId: String,
    val contentHash: String,
    val lastSeenAt: Long,
    val state: String,
    val candidateId: String?
)

/** 알림 재연결 시 중복 후보 생성을 막기 위한 모바일 로컬 정책이다. */
object NotificationEventPolicy {
    const val RETENTION_MS = 7L * 24L * 60L * 60L * 1000L
    const val MAX_EVENT_COUNT = 512
    const val STATE_OBSERVED = "observed"
    const val STATE_PENDING = "pending"
    const val STATE_CONSUMED = "consumed"

    fun eventId(packageName: String, notificationKey: String, postTime: Long): String =
        sha256("$packageName|$notificationKey|$postTime").take(24)

    fun contentHash(rawText: String): String = sha256(rawText)

    fun prune(
        events: List<ProcessedNotificationEvent>,
        now: Long
    ): List<ProcessedNotificationEvent> {
        val cutoff = now - RETENTION_MS
        return events
            .filter { it.lastSeenAt >= cutoff }
            .sortedByDescending { it.lastSeenAt }
            .distinctBy { it.eventId }
            .take(MAX_EVENT_COUNT)
    }

    private fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(value.toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { "%02x".format(it) }
    }
}
