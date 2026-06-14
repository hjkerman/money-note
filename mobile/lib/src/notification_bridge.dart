import 'dart:convert';

import 'package:flutter/services.dart';

import 'models.dart';

class NotificationBridge {
  static const _channel = MethodChannel('money_note/notifications');

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
}
