@Timeout(Duration(minutes: 8))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late Map<String, dynamic> wire;
  late E4Harness h;
  late FrozenGeneration frozen;
  void Function(String)? hook;
  final evidence = <Map<String, dynamic>>[];
  File source() => File('${h.workspace.root.path}/e4-source.json');
  Map<String, dynamic> disk() {
    final d = sqlite3.open(h.store.path);
    try {
      return {
        'source': base64Encode(source().readAsBytesSync()),
        'B': base64Encode(h.baselineFile.readAsBytesSync()),
        'pending': base64Encode(h.pendingFile.readAsBytesSync()),
        for (final table in [
          'accepted',
          'installed',
          'frozen',
          'generation_roots',
          'objects',
        ])
          table: d
              .select('SELECT * FROM $table ORDER BY 1,2')
              .map(
                (r) => r.map(
                  (k, v) => MapEntry(k, v is List<int> ? localChecksum(v) : v),
                ),
              )
              .toList(),
      };
    } finally {
      d.close();
    }
  }

  Future<void> independentRead() async {
    h.reopen();
    final b = await E4Workspace(h.root)
        .readFrozenBaseline(h.store, frozen.id, 1);
    expect(b.serverStateFingerprint, frozen.binding['legacy_fingerprint']);
    final repo = Directory.current.parent.path;
    final p = await Process.run('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66e4-audit/state_oracle.py',
      h.store.path,
      h.workspace.root.path,
    ]);
    expect(p.exitCode, 0, reason: '${p.stderr}');
  }

  setUpAll(() async {
    bridge = await BackendBridge.start(history: 11);
    wire = await e4WireOracle();
  });
  tearDownAll(() async {
    const out = String.fromEnvironment('NR_PROVENANCE_OUTPUT');
    if (out.isNotEmpty) File(out).writeAsStringSync(jsonEncode(evidence));
    await bridge.dispose();
  });
  setUp(() async {
    await bridge.command({'command': 'advance', 'seconds': 901});
    hook = null;
    h = await E4Harness.create(bridge, wire, fault: (p) => hook?.call(p));
    await h.workspace.beginOnlineWrite(1);
    frozen = (await h.install()).frozen;
    await h.state.refreshSegmentedForIsolatedUse(h.store);
  });
  tearDown(() {
    hook = null;
    h.dispose();
  });

  for (final field in ['principal_id', 'dataset_id', 'epoch']) {
    test(
      'NP-$field foreign native predecessor preserves current Frozen readable association',
      () async {
        await bridge.command({'command': 'mutate'});
        await h.publish();
        h.workspace.prepareSegmentedSource(
          h.store,
          h.store.acceptedGeneration(),
          () {},
        );
        final valid = source().readAsBytesSync();
        final s = jsonDecode(source().readAsStringSync());
        final t = h.store.acceptedGeneration().manifest!.target.toJson()
          ..remove('sync_root');
        if (field == 'principal_id') {
          t[field] = 2;
        } else {
          t['ns'][field] = syncUuid();
        }
        t['sync_root'] = objectHash('view', encodeC1(t));
        s['previous_source']['namespace'] = CacheNamespace.forTarget(
          syntheticOrigin,
          SyncTarget.parse(t),
        ).key;
        source().writeAsStringSync(jsonEncode(s), flush: true);
        final before = disk();
        await expectLater(
          h.state.refreshSegmentedForIsolatedUse(h.store),
          throwsA(isA<SegmentedException>()),
        );
        expect(disk(), before);
        await independentRead(); // read-only F0 integrity; recovery remains blocked.
        expect(disk(), before);
        evidence.add({
          'id': 'NP-$field',
          'before': before,
          'after': disk(),
          'retained_read': true,
        });
        source().writeAsBytesSync(valid, flush: true);
        await h.workspace.recoverLegacyHandoff(h.store);
      },
    );
  }

  test('NP-lineage identical Snapshot content with changed synced_at is not prior lineage', () async {
    final original = h.baselineFile.readAsBytesSync();
    final value = jsonDecode(h.baselineFile.readAsStringSync());
    value['synced_at'] = '2026-10-30T00:00:00.000Z';
    h.baselineFile.writeAsStringSync(jsonEncode(value), flush: true);
    final before = disk();
    await expectLater(
      h.state.refreshSegmentedForIsolatedUse(h.store),
      throwsA(isA<SegmentedException>()),
    );
    expect(disk(), before);
    evidence.add({'id': 'NP-lineage', 'before': before, 'after': disk()});
    h.baselineFile.writeAsBytesSync(original, flush: true);
    await independentRead();
  });

  test(
    'NP-receipt truncated required receipt cannot become native success',
    () async {
      final d = sqlite3.open(h.store.path);
      final sql =
          d
                  .select(
                    "SELECT sql FROM sqlite_master WHERE name='immutable_generation'",
                  )
                  .single['sql']
              as String;
      final original = List<int>.from(
        d.select('SELECT receipt FROM generations WHERE id=?', [
              frozen.generationId,
            ]).single['receipt']
            as List<int>,
      );
      d.execute('DROP TRIGGER immutable_generation');
      d.execute('UPDATE generations SET receipt=? WHERE id=?', [
        original.sublist(0, original.length - 1),
        frozen.generationId,
      ]);
      d.execute(sql);
      final before = disk();
      try {
        await expectLater(
          h.state.refreshSegmentedForIsolatedUse(h.store),
          throwsA(isA<SegmentedException>()),
        );
        expect(disk(), before);
        evidence.add({'id': 'NP-receipt', 'before': before, 'after': disk()});
      } finally {
        d.execute('DROP TRIGGER immutable_generation');
        d.execute('UPDATE generations SET receipt=? WHERE id=?', [
          original,
          frozen.generationId,
        ]);
        d.execute(sql);
        d.close();
      }
      await independentRead();
    },
  );

  test(
    'NP-pin removed after E3 acceptance cannot pass source preparation',
    () async {
      final before = disk();
      final d = sqlite3.open(h.store.path);
      final sql =
          d
                  .select(
                    "SELECT sql FROM sqlite_master WHERE name='retained_root_delete'",
                  )
                  .single['sql']
              as String;
      final pin = d.select(
        'SELECT hash FROM generation_roots WHERE generation_id=? LIMIT 1',
        [frozen.generationId],
      ).single['hash'];
      var changed = false;
      hook = (p) {
        if (p != 'after_e3_acceptance') return;
        hook = null;
        d.execute('DROP TRIGGER retained_root_delete');
        d.execute(
          'DELETE FROM generation_roots WHERE generation_id=? AND hash=?',
          [frozen.generationId, pin],
        );
        d.execute(sql);
        changed = true;
      };
      try {
        await expectLater(
          h.state.refreshSegmentedForIsolatedUse(h.store),
          throwsA(isA<SegmentedException>()),
        );
        expect(changed, true);
        final after = disk();
        for (final field in [
          'source',
          'B',
          'pending',
          'installed',
          'frozen',
          'objects',
        ]) {
          expect(after[field], before[field]);
        }
        evidence.add({'id': 'NP-pin', 'before': before, 'after': after});
      } finally {
        d.execute(
          'INSERT INTO generation_roots(generation_id,hash) VALUES(?,?)',
          [frozen.generationId, pin],
        );
        d.close();
      }
      await independentRead();
    },
  );
}
