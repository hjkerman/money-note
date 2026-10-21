import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_files.dart';
import '../../../mobile/test/support/logical_cost_sqlite.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('B03 independent process Frozen recovery has actual primitive/SQL/file accounting', () async {
    const input = String.fromEnvironment('B03_FRESH_INPUT');
    const output = String.fromEnvironment('B03_FRESH_OUTPUT');
    expect(input, isNotEmpty);
    expect(output, isNotEmpty);
    final data = jsonDecode(File(input).readAsStringSync()) as Map;
    final root = Directory(data['root']);
    final target = SyncTarget.parse(data['target']);
    final c = LogicalCost(), sql = SqlCosts(), files = SqlCosts();
    final store = SegmentedClientStore.open(
      root,
      CacheNamespace.forTarget(data['origin'], target),
      adapters: true,
      diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), sql),
    );
    try {
      final workspace = E4Workspace(root);
      final b = await c.run(
        LogicalCostStage.recovery,
        () => CostIo(root, files).run(
          () => workspace.readFrozenBaseline(
            store,
            data['frozen'],
            target.principalId,
          ),
        ),
      );
      expect(b.serverStateFingerprint, data['fingerprint']);
      expect(
        files.values['recovery/file/baseline/decodeCompletedBytes'],
        isNotNull,
      );
      expect(
        c.snapshot().keys.any((k) => k.startsWith('recovery/legacyHash/')),
        true,
      );
      File(output).writeAsStringSync(
        jsonEncode({
          'schema_version': 1,
          'fingerprint': b.serverStateFingerprint,
          'primitive': c.snapshot(),
          'sqlite': sql.snapshot(),
          'files': files.snapshot(),
          'full_recoveries': store.work.snapshot()['frozen_full_recoveries'],
        }),
      );
    } finally {
      store.close();
    }
  });
}
