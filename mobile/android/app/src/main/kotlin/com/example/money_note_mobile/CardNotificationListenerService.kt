package com.example.money_note_mobile

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.security.MessageDigest

class CardNotificationListenerService : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (!AllowedCardApps.contains(sbn.packageName)) return
        val candidate = parseCandidate(sbn) ?: return
        NotificationCandidateStore.append(applicationContext, candidate)
    }

    private fun parseCandidate(sbn: StatusBarNotification): NotificationCandidate? {
        val text = notificationText(sbn.notification)
        val match = CARD_APPROVAL_REGEX.find(text) ?: return null
        val place = text.lines().map { it.trim() }.lastOrNull { it.isNotEmpty() } ?: return null
        val amount = match.groupValues[5].replace(",", "").toIntOrNull() ?: return null
        val cardLast4 = match.groupValues[1]
        val monthDay = "${match.groupValues[2]}/${match.groupValues[3]}"
        val time = match.groupValues[4]
        return NotificationCandidate(
            id = stableId("${sbn.packageName}|$cardLast4|$monthDay|$time|$amount|$place"),
            capturedAt = System.currentTimeMillis(),
            cardLast4 = cardLast4,
            monthDay = monthDay,
            time = time,
            amount = amount,
            usagePlace = place
        )
    }

    private fun notificationText(notification: Notification): String {
        val extras = notification.extras
        val parts = listOfNotNull(
            extras.getCharSequence(Notification.EXTRA_TITLE)?.toString(),
            extras.getCharSequence(Notification.EXTRA_TEXT)?.toString(),
            extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString(),
            extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString()
        )
        return parts.joinToString("\n")
    }

    private fun stableId(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { "%02x".format(it) }.take(24)
    }

    companion object {
        private val CARD_APPROVAL_REGEX =
            Regex("""\[일시불\.승인\((\d{4})\)\](\d{2})/(\d{2})\s+(\d{2}:\d{2})\s+([\d,]+)원""")
    }
}

object AllowedCardApps {
    private val packages = setOf(
        "com.wooricard.smartapp",
        "com.wooricard.wcard",
        "com.wooribank.smart.npib"
    )

    fun contains(packageName: String): Boolean = packages.contains(packageName)
}
