import 'dart:convert';

import 'package:flutter/services.dart';

import 'models.dart';

class NotificationBridge {
  static const _channel = MethodChannel('money_note/notifications');

  Future<NotificationPermissionStatus> permissionStatus() async {
    try {
      final raw =
          await _channel.invokeMapMethod<String, bool>('permissionStatus');
      return NotificationPermissionStatus(
        listenerEnabled: raw?['listener_enabled'] ?? true,
        appNotificationsEnabled: raw?['app_notifications_enabled'] ?? true,
      );
    } on MissingPluginException {
      return const NotificationPermissionStatus.ready();
    }
  }

  Future<List<PendingCardNotification>> listPending() async {
    final raw = await _channel.invokeMethod<String>('listPending') ?? '[]';
    final decoded = jsonDecode(raw);
    if (decoded is! List) return [];
    return decoded
        .map((item) =>
            PendingCardNotification.fromJson(item as Map<String, dynamic>))
        .where((item) => item.id.isNotEmpty)
        .toList();
  }

  Future<void> deletePending(String id) async {
    await _channel.invokeMethod<bool>('deletePending', {'id': id});
  }

  Future<void> openSettings() async {
    await _channel.invokeMethod<bool>('openSettings');
  }

  Future<void> openAppNotificationSettings() async {
    await _channel.invokeMethod<bool>('openAppNotificationSettings');
  }

  Future<void> requestAppNotifications() async {
    await _channel.invokeMethod<bool>('requestAppNotifications');
  }
}

class NotificationPermissionStatus {
  const NotificationPermissionStatus({
    required this.listenerEnabled,
    required this.appNotificationsEnabled,
  });

  const NotificationPermissionStatus.ready()
      : listenerEnabled = true,
        appNotificationsEnabled = true;

  final bool listenerEnabled;
  final bool appNotificationsEnabled;

  bool get isReady => listenerEnabled && appNotificationsEnabled;
}
