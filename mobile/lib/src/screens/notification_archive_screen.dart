import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../notification_bridge.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class CapturedNotificationLogScreen extends StatefulWidget {
  const CapturedNotificationLogScreen({
    required this.state,
    this.initialSource = 'woori_card',
    super.key,
  });

  final AppState state;
  final String initialSource;

  @override
  State<CapturedNotificationLogScreen> createState() =>
      _CapturedNotificationLogScreenState();
}

class _CapturedNotificationLogScreenState
    extends State<CapturedNotificationLogScreen> {
  static const sources = [
    _CapturedSourceSpec(
      source: 'woori_card',
      tabLabel: '우리카드',
      title: '우리카드 알림',
      emptyText: '최근 우리카드 알림 로그가 없습니다.',
    ),
    _CapturedSourceSpec(
      source: 'highway_toll',
      tabLabel: '통행료',
      title: '고속도로통행료+ 알림',
      emptyText: '최근 통행료 알림 로그가 없습니다.',
      note: '파싱 결과와 원문을 함께 보관합니다. 후보 등록 전에는 서버로 전송하지 않습니다.',
    ),
  ];

  final bridge = NotificationBridge();
  late Future<Map<String, List<CapturedNotificationLog>>> logsFuture;

  @override
  void initState() {
    super.initState();
    logsFuture = _load();
  }

  @override
  Widget build(BuildContext context) {
    final initialIndex = sources.indexWhere(
      (source) => source.source == widget.initialSource,
    );
    return DefaultTabController(
      length: sources.length,
      initialIndex: initialIndex < 0 ? 0 : initialIndex,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('최근 납치한 알림'),
          bottom: TabBar(
            tabs: sources.map((source) => Tab(text: source.tabLabel)).toList(),
          ),
        ),
        body: FutureBuilder<Map<String, List<CapturedNotificationLog>>>(
          future: logsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting &&
                snapshot.data == null) {
              return const Center(child: CircularProgressIndicator());
            }
            final logsBySource = snapshot.data ?? const {};
            return TabBarView(
              children: sources.map((source) {
                return _CapturedLogTab(
                  source: source.source,
                  title: source.title,
                  emptyText: source.emptyText,
                  note: source.note,
                  logs: logsBySource[source.source] ?? const [],
                  onRefresh: _reload,
                  onShareAll: _shareAll,
                  onShare: _shareOne,
                  onDelete: _deleteLog,
                  onClear: _clearLogs,
                );
              }).toList(),
            );
          },
        ),
      ),
    );
  }

  Future<Map<String, List<CapturedNotificationLog>>> _load() async {
    final values = await Future.wait(
      sources.map((source) => bridge.listCapturedLogs(source.source)),
    );
    return {
      for (var index = 0; index < sources.length; index += 1)
        sources[index].source: values[index],
    };
  }

  Future<void> _reload() async {
    await widget.state.refreshNotificationInboxState(notify: true);
    if (!mounted) return;
    setState(() {
      logsFuture = _load();
    });
    await logsFuture;
  }

  Future<void> _shareAll(String source) async {
    final text = await bridge.capturedLogText(source);
    final directory = await getTemporaryDirectory();
    final slug = _capturedSourceSlug(source);
    final file =
        File('${directory.path}/money-note-$slug-notification-log.txt');
    await file.writeAsString(text, flush: true);
    await SharePlus.instance.share(
      ShareParams(
        files: [
          XFile(
            file.path,
            mimeType: 'text/plain',
            name: 'money-note-$slug-notification-log.txt',
          ),
        ],
        text: 'Money-Note ${_capturedSourceLabel(source)} 알림 로그',
      ),
    );
  }

  Future<void> _shareOne(CapturedNotificationLog log) async {
    await SharePlus.instance.share(
      ShareParams(
        text: _capturedLogText(log),
        subject: 'Money-Note ${_capturedSourceLabel(log.source)} 알림',
      ),
    );
  }

  Future<void> _deleteLog(CapturedNotificationLog log) async {
    await bridge.deleteCapturedLog(log.source, log.id);
    await _reload();
  }

  Future<void> _clearLogs(String source) async {
    final label = _capturedSourceLabel(source);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('로그 전체 삭제'),
        content: Text(
          '최근 $label 알림 로그를 모두 삭제할까요?'
          ' 후보함은 건드리지 않습니다.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('전체 삭제'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await bridge.clearCapturedLogs(source);
    await _reload();
  }
}

class _CapturedSourceSpec {
  const _CapturedSourceSpec({
    required this.source,
    required this.tabLabel,
    required this.title,
    required this.emptyText,
    this.note,
  });

  final String source;
  final String tabLabel;
  final String title;
  final String emptyText;
  final String? note;
}

class _CapturedLogTab extends StatelessWidget {
  const _CapturedLogTab({
    required this.source,
    required this.title,
    required this.emptyText,
    required this.logs,
    required this.onRefresh,
    required this.onShareAll,
    required this.onShare,
    required this.onDelete,
    required this.onClear,
    this.note,
  });

  final String source;
  final String title;
  final String emptyText;
  final String? note;
  final List<CapturedNotificationLog> logs;
  final Future<void> Function() onRefresh;
  final Future<void> Function(String source) onShareAll;
  final Future<void> Function(CapturedNotificationLog log) onShare;
  final Future<void> Function(CapturedNotificationLog log) onDelete;
  final Future<void> Function(String source) onClear;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
        children: [
          if (note != null) ...[
            MoneyCard(
              child: Text(
                note!,
                style: const TextStyle(
                  color: moneyMuted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: logs.isEmpty ? null : () => onShareAll(source),
                  child: const Text('로그 공유'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton(
                  onPressed: logs.isEmpty ? null : () => onClear(source),
                  child: const Text('전체 삭제'),
                ),
              ),
            ],
          ),
          SectionTitle(
            title,
            trailing: Text(
              '${logs.length}건',
              style: const TextStyle(color: moneyMuted),
            ),
          ),
          if (logs.isEmpty)
            MoneyCard(child: Text(emptyText))
          else
            ...logs.map(
              (log) => _CapturedLogCard(
                log: log,
                onShare: () => onShare(log),
                onDelete: () => onDelete(log),
              ),
            ),
        ],
      ),
    );
  }
}

class _CapturedLogCard extends StatelessWidget {
  const _CapturedLogCard({
    required this.log,
    required this.onShare,
    required this.onDelete,
  });

  final CapturedNotificationLog log;
  final VoidCallback onShare;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    _capturedAt(log.capturedAt),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                IconButton(
                  tooltip: '공유',
                  onPressed: onShare,
                  icon: const Icon(Icons.share_outlined),
                ),
                IconButton(
                  tooltip: '삭제',
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
            _Field(label: 'Parse Status', value: log.parseStatus),
            _Field(label: 'Failure Reason', value: log.parseFailureReason),
            _Field(label: 'Package', value: log.packageName),
            _Field(label: 'Title', value: log.title),
            _Field(label: 'Text', value: log.text),
            _Field(label: 'BigText', value: log.bigText),
            _Field(label: 'SubText', value: log.subText),
            _Field(label: 'TextLines', value: log.textLines.join('\n')),
            _Field(label: 'RawText', value: log.rawText),
            _Field(label: 'NotificationKey', value: log.notificationKey),
            _Field(
              label: 'PostTime',
              value: log.postTime == 0 ? '' : log.postTime.toString(),
            ),
            _Field(label: 'IsOngoing', value: log.isOngoing.toString()),
            _Field(label: 'Category', value: log.category),
            _Field(label: 'card_last4', value: log.cardLast4),
            _Field(label: 'entry_date', value: log.entryDate),
            _Field(
              label: 'amount',
              value: log.amount == 0 ? '' : won(log.amount),
            ),
            _Field(label: 'merchant', value: log.merchant),
          ],
        ),
      ),
    );
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
          Text(
            '$label:',
            style: const TextStyle(
              color: moneyMuted,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 2),
          SelectableText(value),
        ],
      ),
    );
  }
}

String _capturedSourceLabel(String source) {
  switch (source) {
    case 'highway_toll':
      return '통행료';
    default:
      return '우리카드';
  }
}

String _capturedSourceSlug(String source) {
  switch (source) {
    case 'highway_toll':
      return 'highway-toll';
    default:
      return 'woori-card';
  }
}

String _capturedLogText(CapturedNotificationLog log) {
  final lines = <String>[
    'capturedAt=${log.capturedAt}',
    'source=${log.source}',
    'packageName=${log.packageName}',
    'title=${log.title}',
    'text=${log.text}',
    'bigText=${log.bigText}',
    'subText=${log.subText}',
    'textLines=${log.textLines.join(' | ')}',
    'rawText=${log.rawText}',
    'notificationKey=${log.notificationKey}',
    'postTime=${log.postTime}',
    'isOngoing=${log.isOngoing}',
    'category=${log.category}',
    'parseStatus=${log.parseStatus}',
    'parseFailureReason=${log.parseFailureReason}',
    'card_last4=${log.cardLast4}',
    'entry_date=${log.entryDate}',
    'amount=${log.amount}',
    'merchant=${log.merchant}',
  ];
  return lines.join('\n');
}

String _capturedAt(int millis) {
  if (millis <= 0) return '-';
  final date = DateTime.fromMillisecondsSinceEpoch(millis);
  return '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')} '
      '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}:${date.second.toString().padLeft(2, '0')}';
}
