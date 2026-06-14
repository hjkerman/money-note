package com.example.money_note_mobile

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.security.MessageDigest

class CardNotificationListenerService : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (!AllowedCardApps.contains(sbn.packageName)) return
        val candidate = parseCandidate(sbn) ?: return
        val inserted = NotificationCandidateStore.append(applicationContext, candidate)
        if (inserted) {
            CandidateCaptureNotifier.show(applicationContext, candidate)
        }
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

object CandidateCaptureNotifier {
    private const val CHANNEL_ID = "card_candidate_capture"
    private const val NOTIFICATION_ID = 4101

    fun show(context: Context, candidate: NotificationCandidate) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "카드 알림 후보",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "카드 알림에서 등록 대기 후보를 만들었을 때 알려줍니다."
            }
            manager.createNotificationChannel(channel)
        }

        val launchIntent = Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(context, CHANNEL_ID)
        } else {
            Notification.Builder(context)
        }
        val notification = builder
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("카드 알림 후보 1건 포착")
            .setContentText("${candidate.usagePlace} ${candidate.amount}원")
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        manager.notify(NOTIFICATION_ID, notification)
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
