package com.example.money_note_mobile

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
                "listPending" -> result.success(NotificationCandidateStore.list(applicationContext))
                "deletePending" -> {
                    val id = call.argument<String>("id")
                    if (id.isNullOrBlank()) {
                        result.error("invalid_id", "삭제할 후보 ID가 없습니다.", null)
                    } else {
                        result.success(NotificationCandidateStore.delete(applicationContext, id))
                    }
                }
                "openSettings" -> {
                    startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }
}
