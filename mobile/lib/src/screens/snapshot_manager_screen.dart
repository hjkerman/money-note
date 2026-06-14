import 'package:flutter/material.dart';

import '../app_state.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class SnapshotManagerScreen extends StatefulWidget {
  const SnapshotManagerScreen({required this.state, super.key});

  final AppState state;

  @override
  State<SnapshotManagerScreen> createState() => _SnapshotManagerScreenState();
}

class _SnapshotManagerScreenState extends State<SnapshotManagerScreen> {
  late Future<List<LocalSnapshotInfo>> snapshotsFuture;

  @override
  void initState() {
    super.initState();
    snapshotsFuture = widget.state.listLocalSnapshots();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('스냅샷 관리')),
      body: FutureBuilder<List<LocalSnapshotInfo>>(
        future: snapshotsFuture,
        builder: (context, snapshot) {
          final snapshots = snapshot.data ?? [];
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
            children: [
              const MoneyCard(
                child: Text(
                  '앱 실행 때마다 서버 스냅샷을 받아 앱 안에 보관합니다. 필요할 때 파일을 공유하거나 복원하거나 오래된 백업을 지울 수 있습니다.',
                  style:
                      TextStyle(color: moneyMuted, fontWeight: FontWeight.w600),
                ),
              ),
              const SizedBox(height: 14),
              if (snapshot.connectionState == ConnectionState.waiting)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: CircularProgressIndicator(),
                  ),
                )
              else if (snapshots.isEmpty)
                const MoneyCard(child: Text('저장된 스냅샷이 없습니다.'))
              else ...[
                ...snapshots.map((item) => _SnapshotCard(
                      snapshot: item,
                      state: widget.state,
                      onChanged: _reload,
                    )),
                const SizedBox(height: 6),
                OutlinedButton(
                  onPressed: widget.state.isBusy ? null : _confirmDeleteAll,
                  style: OutlinedButton.styleFrom(foregroundColor: moneyRed),
                  child: const Text('스냅샷 전체 삭제'),
                ),
              ],
            ],
          );
        },
      ),
    );
  }

  void _reload() {
    setState(() {
      snapshotsFuture = widget.state.listLocalSnapshots();
    });
  }

  Future<void> _confirmDeleteAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('스냅샷 전체 삭제'),
        content: const Text('앱 안에 저장된 스냅샷 파일을 모두 삭제할까요? 서버 데이터는 건드리지 않습니다.'),
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
    if (confirmed == true) {
      await widget.state.deleteAllLocalSnapshots();
      _reload();
    }
  }
}

class _SnapshotCard extends StatelessWidget {
  const _SnapshotCard({
    required this.snapshot,
    required this.state,
    required this.onChanged,
  });

  final LocalSnapshotInfo snapshot;
  final AppState state;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_title(snapshot.updatedAt),
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 6),
            Text(_subtitle(snapshot),
                style: const TextStyle(
                    color: moneyMuted, fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: state.isBusy
                        ? null
                        : () => state.shareLocalSnapshot(snapshot.filename),
                    child: const Text('공유'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: state.isBusy ? null : () => _restore(context),
                    child: const Text('복원'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: state.isBusy ? null : () => _delete(context),
                    style: OutlinedButton.styleFrom(foregroundColor: moneyRed),
                    child: const Text('삭제'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _delete(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('스냅샷 삭제'),
        content: Text('${_title(snapshot.updatedAt)} 스냅샷을 삭제할까요?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('삭제'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await state.deleteLocalSnapshot(snapshot.filename);
      onChanged();
    }
  }

  Future<void> _restore(BuildContext context) async {
    final password = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('스냅샷 복원'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
                '${_title(snapshot.updatedAt)} 상태로 복원할까요? 현재 장부 운용 데이터가 교체됩니다.'),
            const SizedBox(height: 12),
            TextField(
              controller: password,
              obscureText: true,
              decoration: const InputDecoration(labelText: '계정 비밀번호'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('복원'),
          ),
        ],
      ),
    );
    if (confirmed == true && password.text.isNotEmpty) {
      await state.restoreLocalSnapshot(
          filename: snapshot.filename, password: password.text);
      onChanged();
    }
    password.dispose();
  }

  String _title(DateTime value) {
    return '${value.year}.${value.month.toString().padLeft(2, '0')}.${value.day.toString().padLeft(2, '0')} ${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
  }

  String _subtitle(LocalSnapshotInfo snapshot) {
    return '${_formatBytes(snapshot.sizeBytes)} · 앱 내부 백업';
  }

  String _formatBytes(int bytes) {
    if (bytes >= 1024 * 1024) {
      return '${(bytes / 1024 / 1024).toStringAsFixed(1)}MB';
    }
    if (bytes >= 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)}KB';
    }
    return '$bytes바이트';
  }
}
