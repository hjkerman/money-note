package com.example.money_note_mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class NotificationEventPolicyTest {
    @Test
    fun `같은 알림 키와 게시 시각은 같은 이벤트 아이디를 만든다`() {
        val first = NotificationEventPolicy.eventId("com.example.card", "key-1", 1000L)
        val second = NotificationEventPolicy.eventId("com.example.card", "key-1", 1000L)

        assertEquals(first, second)
    }

    @Test
    fun `같은 알림 키를 다시 사용해도 게시 시각이 다르면 새 이벤트다`() {
        val first = NotificationEventPolicy.eventId("com.example.card", "key-1", 1000L)
        val second = NotificationEventPolicy.eventId("com.example.card", "key-1", 2000L)

        assertNotEquals(first, second)
    }

    @Test
    fun `처리 이력은 마지막 관측 후 7일까지만 유지한다`() {
        val now = NotificationEventPolicy.RETENTION_MS + 1000L
        val retained = NotificationEventPolicy.prune(
            listOf(
                event("expired", 999L),
                event("boundary", 1000L),
                event("recent", now)
            ),
            now
        )

        assertEquals(listOf("recent", "boundary"), retained.map { it.eventId })
    }

    @Test
    fun `처리 이력은 최신 512건까지만 유지한다`() {
        val events = (0 until 600).map { index -> event("event-$index", index.toLong()) }

        val retained = NotificationEventPolicy.prune(events, 600L)

        assertEquals(512, retained.size)
        assertEquals("event-599", retained.first().eventId)
        assertEquals("event-88", retained.last().eventId)
    }

    private fun event(id: String, lastSeenAt: Long) = ProcessedNotificationEvent(
        eventId = id,
        contentHash = "content-$id",
        lastSeenAt = lastSeenAt,
        state = NotificationEventPolicy.STATE_OBSERVED,
        candidateId = null
    )
}
