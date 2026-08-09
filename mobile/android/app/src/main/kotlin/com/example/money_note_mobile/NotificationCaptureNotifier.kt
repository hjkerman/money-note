package com.example.money_note_mobile

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build

/** 알림 파싱 실패와 수동 확인 필요 상태를 Android 알림으로 전달한다. */
object NotificationCaptureNotifier {
    private const val LEGACY_TOLL_CHANNEL_ID = "money_note_highway_toll_candidates"
    private const val FAILURE_CHANNEL_ID = "money_note_notification_parse_failures"
    private const val LEGACY_TOLL_SUMMARY_ID = 8301
    private const val FAILURE_SUMMARY_ID = 8302

    /** 통합 배너 도입 전에 남은 통행료 전용 성공 알림을 정리한다. */
    fun retireHighwayTollSuccessNotifications(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.cancel(LEGACY_TOLL_SUMMARY_ID)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.deleteNotificationChannel(LEGACY_TOLL_CHANNEL_ID)
        }
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
}
