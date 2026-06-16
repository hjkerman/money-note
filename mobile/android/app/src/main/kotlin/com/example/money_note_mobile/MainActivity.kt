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
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "money_note/notifications").setMethodCallHandler { call, result ->
            when (call.method) {
                "listRawArchive" -> result.success(NotificationCandidateStore.listRaw(applicationContext))
                "rawArchiveLogText" -> result.success(NotificationCandidateStore.logText(applicationContext))
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
                "permissionStatus" -> result.success(permissionStatus())
                else -> result.notImplemented()
            }
        }
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
