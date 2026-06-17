package com.example.money_note_mobile

import android.Manifest
import android.app.NotificationManager
import android.net.Uri
import android.os.Build
import android.content.Intent
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object {
        const val ACTION_OPEN_NOTIFICATION_IMPORT = "com.example.money_note_mobile.OPEN_NOTIFICATION_IMPORT"
        const val EXTRA_OPEN_NOTIFICATION_IMPORT = "open_notification_import"
        private var pendingNotificationImportOpen = false
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        captureLaunchTarget(intent)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "money_note/notifications").setMethodCallHandler { call, result ->
            when (call.method) {
                "configureCards" -> {
                    NotificationCandidateStore.configureCards(
                        applicationContext,
                        call.argument<String>("owner_card_last4").orEmpty(),
                        call.argument<String>("family_card_last4").orEmpty()
                    )
                    result.success(true)
                }
                "listCandidates" -> result.success(NotificationCandidateStore.listCandidates(applicationContext))
                "candidateCounts" -> result.success(NotificationCandidateStore.candidateCounts(applicationContext))
                "manualReviewCount" -> result.success(NotificationCandidateStore.manualReviewCount(applicationContext))
                "deleteCandidate" -> result.success(NotificationCandidateStore.deleteCandidate(applicationContext, call.argument<String>("id").orEmpty()))
                "clearCandidatesByRole" -> result.success(NotificationCandidateStore.clearCandidatesByRole(applicationContext, call.argument<String>("role").orEmpty()))
                "listWooriLogs" -> result.success(NotificationCandidateStore.listWooriLogs(applicationContext))
                "wooriLogText" -> result.success(NotificationCandidateStore.wooriLogText(applicationContext))
                "deleteWooriLog" -> result.success(NotificationCandidateStore.deleteWooriLog(applicationContext, call.argument<String>("id").orEmpty()))
                "clearWooriLogs" -> result.success(NotificationCandidateStore.clearWooriLogs(applicationContext))
                "openSettings" -> {
                    startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                    result.success(true)
                }
                "openAppNotificationSettings" -> {
                    openAppNotificationSettings()
                    result.success(true)
                }
                "requestAppNotifications" -> {
                    requestAppNotificationPermission()
                    result.success(true)
                }
                "consumeLaunchTarget" -> result.success(consumeLaunchTarget())
                "permissionStatus" -> result.success(permissionStatus())
                else -> result.notImplemented()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        captureLaunchTarget(intent)
    }

    private fun captureLaunchTarget(intent: Intent?) {
        if (intent?.action == ACTION_OPEN_NOTIFICATION_IMPORT ||
            intent?.getBooleanExtra(EXTRA_OPEN_NOTIFICATION_IMPORT, false) == true) {
            pendingNotificationImportOpen = true
        }
    }

    private fun consumeLaunchTarget(): String {
        if (!pendingNotificationImportOpen) return ""
        pendingNotificationImportOpen = false
        return "notification_import"
    }

    private fun permissionStatus(): Map<String, Boolean> {
        return mapOf(
            "listener_enabled" to isNotificationListenerEnabled(),
            "app_notifications_enabled" to areAppNotificationsEnabled()
        )
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val enabled = Settings.Secure.getString(
            contentResolver,
            "enabled_notification_listeners"
        ) ?: return false
        return enabled.split(":").any { item ->
            item.contains(packageName, ignoreCase = true)
        }
    }

    private fun areAppNotificationsEnabled(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return true
        val manager = getSystemService(NotificationManager::class.java)
        return manager.areNotificationsEnabled()
    }

    private fun requestAppNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 4102)
        } else {
            openAppNotificationSettings()
        }
    }

    private fun openAppNotificationSettings() {
        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                .putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
        } else {
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                .setData(Uri.parse("package:$packageName"))
        }
        startActivity(intent)
    }
}
