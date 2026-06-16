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

  Future<void> configureCards({
    required String ownerCardLast4,
    required String familyCardLast4,
  }) async {
    try {
      await _channel.invokeMethod<bool>('configureCards', {
        'owner_card_last4': ownerCardLast4,
        'family_card_last4': familyCardLast4,
      });
    } on MissingPluginException {
      return;
    }
  }

  Future<List<CardNotificationCandidate>> listCandidates() async {
    final raw = await _invokeJsonList('listCandidates');
    return raw
        .map((item) =>
            CardNotificationCandidate.fromJson(item as Map<String, dynamic>))
        .where((item) => item.id.isNotEmpty)
        .toList();
  }

  Future<List<WooriNotificationLog>> listWooriLogs() async {
    final raw = await _invokeJsonList('listWooriLogs');
    return raw
        .map((item) =>
            WooriNotificationLog.fromJson(item as Map<String, dynamic>))
        .where((item) => item.id.isNotEmpty)
        .toList();
  }

  Future<NotificationCandidateCounts> candidateCounts() async {
    try {
      final raw =
          await _channel.invokeMapMethod<String, int>('candidateCounts');
      final manualReview =
          await _channel.invokeMethod<int>('manualReviewCount') ?? 0;
      return NotificationCandidateCounts(
        owner: raw?['owner'] ?? 0,
        family: raw?['family'] ?? 0,
        manualReview: manualReview,
      );
    } on MissingPluginException {
      return const NotificationCandidateCounts.empty();
    }
  }

  Future<void> deleteCandidate(String id) async {
    await _channel.invokeMethod<int>('deleteCandidate', {'id': id});
  }

  Future<void> clearCandidatesByRole(String role) async {
    await _channel.invokeMethod<int>('clearCandidatesByRole', {'role': role});
  }

  Future<void> deleteWooriLog(String id) async {
    await _channel.invokeMethod<int>('deleteWooriLog', {'id': id});
  }

  Future<void> clearWooriLogs() async {
    await _channel.invokeMethod<int>('clearWooriLogs');
  }

  Future<String> wooriLogText() async {
    return await _channel.invokeMethod<String>('wooriLogText') ?? '';
  }

  Future<List<dynamic>> _invokeJsonList(String method) async {
    try {
      final raw = await _channel.invokeMethod<String>(method) ?? '[]';
      final decoded = jsonDecode(raw);
      return decoded is List ? decoded : const [];
    } on MissingPluginException {
      return const [];
    }
  }

  Future<List<CardNotificationCandidate>> listRawArchive() async {
    return listCandidates();
  }

  Future<String> rawArchiveLogText() async {
    return wooriLogText();
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
