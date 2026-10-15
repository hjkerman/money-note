import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

// Only the disposable instrumented copy has audit_trace.dart.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('independent fresh-process Frozen-B read cost', () async {
    const path = String.fromEnvironment('REAUDIT_FRESH_JOB');
    final job = jsonDecode(File(path).readAsStringSync());
    final root = Directory(job['root']);
    expect(
      File('${root.path}/reaudit-owned').readAsStringSync(),
      'synthetic cost',
    );
    final store = SegmentedClientStore.open(
      root,
      CacheNamespace.forTarget(job['origin'], SyncTarget.parse(job['target'])),
      adapters: true,
    );
    try {
      final workspace = E4Workspace(root);
      AuditTrace.reset('fresh_process_cold');
      final timer = Stopwatch()..start();
      final view = await workspace.readFrozenPending(store, job['frozen'], 1);
      timer.stop();
      final events = AuditTrace.stop();
      int sum(String key) =>
          events.fold(0, (n, e) => n + (e[key] as int? ?? 0));
      File(job['output']).writeAsStringSync(
        jsonEncode({
          'sql': events.where((e) => e.containsKey('sql')).length,
          'body_bytes': sum('body_bytes_read'),
          'returned_rows': sum('rows_returned'),
          'raw_nodes': sum('raw_objects_read'),
          'index_nodes': sum('index_objects_read'),
          'full_verify_calls': events
              .where((e) => e['note'] == 'full_verify')
              .length,
          'legacy_full_reads': events
              .where((e) => e['note'] == 'legacy_full_read')
              .length,
          'pin_insert': sum('pin_insert'),
          'pin_delete': sum('pin_delete'),
          'pin_update': sum('pin_update'),
          'elapsed_us': timer.elapsedMicroseconds,
          'lineage': workspace.recoveryLineageFingerprint(view.bundle.baseline),
          'operations': view.bundle.operations.map((o) => o.toJson()).toList(),
        }),
        flush: true,
      );
    } finally {
      store.close();
    }
  });
}
