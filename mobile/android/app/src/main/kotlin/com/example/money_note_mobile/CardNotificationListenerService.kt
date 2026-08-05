package com.example.money_note_mobile

import android.app.Notification
import android.content.ComponentName
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

class CardNotificationListenerService : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        processNotification(sbn, recovered = false)
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        val active = try {
            activeNotifications.orEmpty()
        } catch (error: Exception) {
            Log.e("MN_NOTIFY", "listener connected, active notification lookup failed", error)
            emptyArray()
        }
        var recoveredCount = 0
        for (sbn in active) {
            if (NotificationSource.fromPackageName(sbn.packageName) == null) continue
            if (processNotification(sbn, recovered = true)) recoveredCount += 1
        }
        Log.i("MN_NOTIFY", "listener connected, active=${active.size}, recovered=$recoveredCount")
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        Log.w("MN_NOTIFY", "listener disconnected; requesting rebind")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            requestRebind(ComponentName(this, CardNotificationListenerService::class.java))
        }
    }

    private fun processNotification(sbn: StatusBarNotification, recovered: Boolean): Boolean {
        return try {
            val record = rawRecord(sbn)
            val result = NotificationCandidateStore.handleNotification(applicationContext, record)
            if (!result.saved) return false
            Log.d(
                "MN_NOTIFY",
                "packageName=${record.packageName}, title=${record.title}, text=${record.text}, " +
                    "bigText=${record.bigText}, rawText=${record.rawText}, saved=${result.saved}, " +
                    "recovered=$recovered, isApprovalCandidate=${result.isApprovalCandidate}, " +
                    "parseStatus=${result.parseStatus}, parseFailureReason=${result.parseFailureReason}, " +
                    "card_last4=${result.parsed.cardLast4}, entry_date=${result.parsed.entryDate}, " +
                    "amount=${result.parsed.amount}, merchant=${result.parsed.merchant}, " +
                    "candidateCreated=${result.candidateCreated}, logCount=${result.logCount}, " +
                    "candidateCount=${result.candidateCount}"
            )
            true
        } catch (error: Exception) {
            Log.e("MN_NOTIFY", "notification processing failed: package=${sbn.packageName}", error)
            false
        }
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
        val id = NotificationEventPolicy.eventId(
            sbn.packageName,
            notificationKey,
            sbn.postTime
        )
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

}
