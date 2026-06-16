package com.example.money_note_mobile

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import java.security.MessageDigest

class CardNotificationListenerService : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val record = rawRecord(sbn)
        val count = NotificationCandidateStore.appendRaw(applicationContext, record)
        Log.d(
            "MN_NOTIFY",
            "packageName=${record.packageName}, title=${record.title}, text=${record.text}, " +
                "bigText=${record.bigText}, rawText=${record.rawText}, saved=true, count=$count"
        )
    }

    private fun rawRecord(sbn: StatusBarNotification): RawNotificationRecord {
        val extras = sbn.notification.extras
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString().orEmpty()
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString().orEmpty()
        val subText = extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString().orEmpty()
        val textLines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)
            ?.map { it?.toString().orEmpty() }
            .orEmpty()
        val rawText = buildList {
            add(title)
            add(text)
            add(bigText)
            add(subText)
            addAll(textLines)
        }.map { it.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
            .joinToString("\n")
        val notificationKey = sbn.key.orEmpty()
        val id = stableId("${sbn.packageName}|$notificationKey|${sbn.postTime}|$rawText")
        return RawNotificationRecord(
            id = id,
            capturedAt = System.currentTimeMillis(),
            packageName = sbn.packageName,
            title = title,
            text = text,
            bigText = bigText,
            subText = subText,
            textLines = textLines,
            rawText = rawText,
            notificationKey = notificationKey,
            postTime = sbn.postTime,
            isOngoing = (sbn.notification.flags and Notification.FLAG_ONGOING_EVENT) != 0,
            category = sbn.notification.category.orEmpty()
        )
    }

    private fun stableId(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { "%02x".format(it) }.take(24)
    }
}
