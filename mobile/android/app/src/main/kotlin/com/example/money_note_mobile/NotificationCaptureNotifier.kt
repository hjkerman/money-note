package com.example.money_note_mobile

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build

/** 알림 후보 생성 결과와 파싱 실패를 Android 알림으로 전달한다. */
object NotificationCaptureNotifier {
    private const val TOLL_CHANNEL_ID = "money_note_highway_toll_candidates"
    private const val FAILURE_CHANNEL_ID = "money_note_notification_parse_failures"
    private const val TOLL_GROUP_KEY = "money_note_highway_toll_capture"
    private const val TOLL_SUMMARY_ID = 8301
    private const val FAILURE_SUMMARY_ID = 8302

    fun notifyHighwayTollCandidate(context: Context, candidate: CardNotificationCandidate) {
        createChannels(context)
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val description = candidateDescription(candidate)
        val notification = builder(context, TOLL_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("통행료 납치 성공")
            .setContentText(description)
            .setContentIntent(importPendingIntent(context, childId(candidate.id)))
            .setGroup(TOLL_GROUP_KEY)
            .setAutoCancel(true)
            .build()
        manager.notify(childId(candidate.id), notification)
    }

    fun cancelHighwayTollCandidate(context: Context, candidateId: String) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.cancel(childId(candidateId))
    }

    fun updateHighwayTollSummary(
        context: Context,
        candidates: List<CardNotificationCandidate>
    ) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (candidates.isEmpty()) {
            manager.cancel(TOLL_SUMMARY_ID)
            return
        }
        createChannels(context)
        val ordered = candidates.sortedByDescending { it.capturedAt }
        val style = Notification.InboxStyle()
            .setSummaryText("미확인 ${ordered.size}건")
        ordered.take(6).forEach { style.addLine(candidateDescription(it)) }
        val notification = builder(context, TOLL_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("통행료 납치 ${ordered.size}건")
            .setContentText(candidateDescription(ordered.first()))
            .setStyle(style)
            .setContentIntent(importPendingIntent(context, TOLL_SUMMARY_ID))
            .setGroup(TOLL_GROUP_KEY)
            .setGroupSummary(true)
            .setOnlyAlertOnce(true)
            .setAutoCancel(false)
            .build()
        manager.notify(TOLL_SUMMARY_ID, notification)
    }

    fun updateFailureSummary(
        context: Context,
        failures: List<CapturedNotificationLog>,
        alert: Boolean
    ) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (failures.isEmpty()) {
            manager.cancel(FAILURE_SUMMARY_ID)
            return
        }
        createChannels(context)
        val ordered = failures.sortedByDescending { it.capturedAt }
        val latest = ordered.first()
        val wooriCount = ordered.count { it.source == NotificationSource.WOORI_CARD.wireName }
        val tollCount = ordered.count { it.source == NotificationSource.HIGHWAY_TOLL.wireName }
        val description = buildList {
            if (wooriCount > 0) add("우리카드 ${wooriCount}건")
            if (tollCount > 0) add("통행료 ${tollCount}건")
        }.joinToString(" · ")
        val notification = builder(context, FAILURE_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("알림 파싱 확인 필요 ${ordered.size}건")
            .setContentText(description)
            .setStyle(Notification.BigTextStyle().bigText(description))
            .setContentIntent(archivePendingIntent(context, latest.source))
            .setOnlyAlertOnce(!alert)
            .setAutoCancel(true)
            .build()
        manager.notify(FAILURE_SUMMARY_ID, notification)
    }

    private fun candidateDescription(candidate: CardNotificationCandidate): String {
        val route = candidate.usageItem.ifBlank { "통행료" }
        val amount = candidate.amount?.let { "%,d원".format(it) } ?: "금액 입력 필요"
        return "$route · $amount"
    }

    private fun importPendingIntent(context: Context, requestCode: Int): PendingIntent {
        val intent = Intent(context, MainActivity::class.java)
            .setAction(MainActivity.ACTION_OPEN_NOTIFICATION_IMPORT)
            .putExtra(MainActivity.EXTRA_OPEN_NOTIFICATION_IMPORT, true)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        return PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    private fun archivePendingIntent(context: Context, source: String): PendingIntent {
        val intent = Intent(context, MainActivity::class.java)
            .setAction(MainActivity.ACTION_OPEN_NOTIFICATION_ARCHIVE)
            .putExtra(MainActivity.EXTRA_NOTIFICATION_ARCHIVE_SOURCE, source)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        return PendingIntent.getActivity(
            context,
            FAILURE_SUMMARY_ID,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    private fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(
                TOLL_CHANNEL_ID,
                "Money-Note 통행료 후보",
                NotificationManager.IMPORTANCE_HIGH
            )
        )
        manager.createNotificationChannel(
            NotificationChannel(
                FAILURE_CHANNEL_ID,
                "Money-Note 알림 파싱 확인",
                NotificationManager.IMPORTANCE_HIGH
            )
        )
    }

    private fun builder(context: Context, channelId: String): Notification.Builder =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(context, channelId)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(context)
        }

    private fun childId(candidateId: String): Int =
        10_000 + (candidateId.hashCode() and 0x3fffffff)
}
