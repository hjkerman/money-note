// Separate-process accepted-read probe; does not invent a legacy/Frozen source.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'logical_cost_sqlite.dart';

Future<void> main(List<String> args) async {
  final input = jsonDecode(File(args.single).readAsStringSync()) as Map;
  final target = SyncTarget.parse(input['target']);
  final c = LogicalCost(), sql = SqlCosts();
  final store = SegmentedClientStore.open(Directory(input['root']),
      CacheNamespace.forTarget(input['origin'], target),
      adapters: true,
      diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), sql));
  try {
    final accepted =
        await c.run(LogicalCostStage.recovery, store.recoverAcceptedGeneration);
    final count = c.run(
        LogicalCostStage.e4Read,
        () => store.withAcceptedRead(
            accepted, (r) => r.rows('ledger_entries', limit: 3).length));
    stdout.writeln(jsonEncode({
      'sync_root': accepted.manifest!.target.syncRoot,
      'rows_read': count,
      'counters': c.snapshot(),
      'sqlite': sql.snapshot()
    }));
  } finally {
    store.close();
  }
}
