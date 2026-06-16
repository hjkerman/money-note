import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../app_state.dart';
import '../models.dart';
import '../notification_bridge.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class NotificationImportScreen extends StatefulWidget {
  const NotificationImportScreen({required this.state, super.key});

  final AppState state;

  @override
  State<NotificationImportScreen> createState() =>
      _NotificationImportScreenState();
}

class _NotificationImportScreenState extends State<NotificationImportScreen> {
  final bridge = NotificationBridge();
  late Future<List<RawNotificationRecord>> archiveFuture;

  @override
  void initState() {
    super.initState();
    archiveFuture = bridge.listRawArchive();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('알림 원문 보관함')),
      body: FutureBuilder<List<RawNotificationRecord>>(
        future: archiveFuture,
        builder: (context, snapshot) {
          final items = snapshot.data ?? [];
          return RefreshIndicator(
            onRefresh: () async => _reload(),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              children: [
                MoneyCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Raw Notification Archive',
                          style: TextStyle(
                              fontSize: 22, fontWeight: FontWeight.w900)),
                      const SizedBox(height: 10),
                      const Text(
                        '최근 알림 100건을 앱 안에만 저장합니다. 지금은 관측용 공사장이라 서버 등록, 자동 후보 생성, 자동 분류를 하지 않습니다.',
                        style: TextStyle(
                            color: moneyMuted, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: _shareLog,
                        child: const Text('txt 로그 공유'),
                      ),
                    ],
                  ),
                ),
                SectionTitle('최근 알림',
                    trailing: Text('${items.length}건',
                        style: const TextStyle(color: moneyMuted))),
                if (snapshot.connectionState == ConnectionState.waiting)
                  const Center(
                      child: Padding(
                          padding: EdgeInsets.all(24),
                          child: CircularProgressIndicator()))
                else if (items.isEmpty)
                  const MoneyCard(child: Text('저장된 알림 원문이 없습니다.'))
                else
                  ...items.map(_RawNotificationCard.new),
              ],
            ),
          );
        },
      ),
    );
  }

  void _reload() {
    setState(() {
      archiveFuture = bridge.listRawArchive();
    });
  }

  Future<void> _shareLog() async {
    final text = await bridge.rawArchiveLogText();
    final directory = await getTemporaryDirectory();
    final file = File('${directory.path}/money-note-notification-log.txt');
    await file.writeAsString(text, flush: true);
    await Share.shareXFiles(
      [
        XFile(file.path,
            mimeType: 'text/plain', name: 'money-note-notification-log.txt')
      ],
      text: 'Money-Note 알림 원문 로그',
    );
  }
}

class _RawNotificationCard extends StatelessWidget {
  const _RawNotificationCard(this.record);

  final RawNotificationRecord record;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_capturedAt(record.capturedAt),
                style:
                    const TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            _Field(label: 'Package', value: record.packageName),
            _Field(label: 'Title', value: record.title),
            _Field(label: 'Text', value: record.text),
            _Field(label: 'BigText', value: record.bigText),
            if (record.textLines.isNotEmpty)
              _Field(label: 'TextLines', value: record.textLines.join('\n')),
            _Field(label: 'SubText', value: record.subText),
            _Field(label: 'Raw', value: record.rawText),
            _Field(label: 'Key', value: record.notificationKey),
            _Field(label: 'PostTime', value: record.postTime.toString()),
            _Field(
                label: 'Ongoing', value: record.isOngoing ? 'true' : 'false'),
            _Field(label: 'Category', value: record.category),
          ],
        ),
      ),
    );
  }

  String _capturedAt(int millis) {
    if (millis <= 0) return '-';
    final date = DateTime.fromMillisecondsSinceEpoch(millis);
    return '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')} '
        '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}:${date.second.toString().padLeft(2, '0')}';
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    if (value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('$label:',
              style: const TextStyle(
                  color: moneyMuted, fontWeight: FontWeight.w800)),
          const SizedBox(height: 2),
          SelectableText(value),
        ],
      ),
    );
  }
}
