@Timeout(Duration(minutes: 5))
library;

import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';
import 'support/e4_targeted_fixture.dart';
import 'support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late Map<String, dynamic> wire;
  late E4Harness h;
  void Function(String)? sqlFault;
  setUpAll(() async {
    bridge = await BackendBridge.start(history: 4);
    wire = await e4WireOracle();
  });
  tearDownAll(() => bridge.dispose());
  setUp(() async {
    sqlFault = null;
    h = await E4Harness.create(bridge, wire,
        sqlFault: (p) => sqlFault?.call(p));
  });
  tearDown(() => h.dispose());
  Set<String> closure(String generation) {
    final d = sqlite3.open(h.store.path);
    try {
      return d
          .select(
              'WITH RECURSIVE c(hash) AS (SELECT hash FROM generation_roots WHERE generation_id=? UNION SELECT e.child FROM edges e JOIN c ON e.parent=c.hash) SELECT hash FROM c',
              [generation])
          .map((r) => r['hash'] as String)
          .toSet();
    } finally {
      d.close();
    }
  }

  test(
      'T02 first durable frozen pin protects exact independently expected graph',
      () async {
    final result = await h.install();
    final oracle = await bridge.command({'command': 'oracle'});
    expect(closure(result.frozen.generationId),
        (oracle['objects'] as List).map((o) => o['ref']['hash']).toSet());
    final d = sqlite3.open(h.store.path);
    expect(
        d.select(
            'SELECT count(*) AS n FROM generation_roots WHERE generation_id=?',
            [result.frozen.generationId]).single['n'],
        4);
    expect(d.select('SELECT generation_id FROM frozen').single['generation_id'],
        result.frozen.generationId);
    expect(d.select('PRAGMA foreign_key_check'), isEmpty);
    d.close();
  });
  test('T02 idempotent installed association never rewrites object/root pins',
      () async {
    final f = (await h.install()).frozen;
    final before = closure(f.generationId), work = h.store.work.snapshot();
    for (var n = 0; n < 3; n++) {
      expect(
          h.store.finishFrozenHandoff(f, finalAuthorityFence: () {}).id, f.id);
    }
    expect(closure(f.generationId), before);
    expect(h.store.work.since(work)['pin_inserts'] ?? 0, 0);
    expect(h.store.frozenGenerations().length, 1);
  });
  test(
      'T02 G1 survives G2 and G3 accepted replacement, not merely previous pin',
      () async {
    final f = (await h.install()).frozen,
        required = closure((h.store.frozenGenerations()).single.generationId);
    for (var n = 0; n < 2; n++) {
      await bridge.command({'command': 'mutate'});
      await h.publish();
    }
    final accepted = h.store.acceptedGeneration();
    expect(accepted.id, isNot(f.generationId));
    expect(accepted.previousId, isNot(f.generationId));
    expect(closure(f.generationId), required);
    final b = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
    expect(
        h.workspace.recoveryLineageFingerprint(b), f.binding['legacy_lineage']);
    expect(h.store.discardUnacceptedGeneration(f.generationId), false);
  });
  test('T02 reopen cold recovery preserves lineage, roots and frozen owner',
      () async {
    final f = (await h.install()).frozen;
    h.reopen();
    final workspace = E4Workspace(h.root);
    final b = await workspace.readFrozenBaseline(h.store, f.id, 1);
    expect(
        workspace.recoveryLineageFingerprint(b), f.binding['legacy_lineage']);
    expect(h.store.work.snapshot()['frozen_full_recoveries'], 1);
    expect(h.store.frozenGenerations().single.installed, true);
  });
  test('T02 logout cannot delete durable frozen retention', () async {
    final f = (await h.install()).frozen;
    final before = closure(f.generationId);
    await h.state.logout();
    expect(h.store.frozenGenerations().single.id, f.id);
    expect(closure(f.generationId), before);
  });
  test('T02 borrowed read disposal cannot release permanent frozen pin',
      () async {
    final f = (await h.install()).frozen;
    await h.store.recoverFrozenGeneration(f.id);
    for (var n = 0; n < 4; n++) {
      h.store.withFrozenRead(f, (v) => v.rows('ledger_entries', limit: 1));
    }
    expect(h.store.frozenGenerations().single.id, f.id);
  });
  test(
      'T02 direct deletion of frozen generation and descendants is rejected before COMMIT',
      () async {
    final f = (await h.install()).frozen;
    final d = sqlite3.open(h.store.path);
    d.execute('PRAGMA foreign_keys=ON');
    for (final sql in [
      'DELETE FROM generations WHERE id=?',
      'DELETE FROM objects WHERE hash=?'
    ]) {
      d.execute('BEGIN IMMEDIATE');
      expect(
          () => d.execute(sql, [
                sql.contains('generations')
                    ? f.generationId
                    : f.target.roots['raw']!.hash
              ]),
          throwsA(isA<SqliteException>()));
      d.execute('ROLLBACK');
    }
    expect(d.select('SELECT count(*) AS n FROM frozen').single['n'], 1);
    d.close();
  });
  test('T02 installed pin has no premature preparation-release path', () async {
    final f = (await h.install()).frozen;
    expect(
        () => h.store.discardFrozenPreparation(f, finalAuthorityFence: () {}),
        throwsA(isA<SegmentedException>()));
    expect(h.store.frozenGenerations().single.id, f.id);
  });
  test('T02 missing mandatory frozen trigger rejects warmed provenance',
      () async {
    final f = (await h.install()).frozen;
    final d = sqlite3.open(h.store.path);
    d.execute('DROP TRIGGER retained_frozen_generation');
    d.close();
    await expectLater(h.workspace.readFrozenBaseline(h.store, f.id, 1),
        throwsA(isA<SegmentedException>()));
    final direct = sqlite3.open(h.store.path);
    expect(direct.select('SELECT count(*) AS n FROM frozen').single['n'], 1);
    direct.close();
  });
  test(
      'T02 externally corrupted binding, even with restored schema, fails closed',
      () async {
    final f = (await h.install()).frozen;
    final d = sqlite3.open(h.store.path);
    final sql = d
        .select(
            "SELECT sql FROM sqlite_master WHERE name='immutable_frozen_binding'")
        .single['sql'] as String;
    d.execute('DROP TRIGGER immutable_frozen_binding');
    d.execute('UPDATE frozen SET checksum=?', ['0' * 64]);
    d.execute(sql);
    d.close();
    await expectLater(h.workspace.readFrozenBaseline(h.store, f.id, 1),
        throwsA(isA<SegmentedException>()));
    expect(h.baselineFile.existsSync(), true);
  });
  test('T02 wrong principal cannot reuse frozen verification evidence',
      () async {
    final f = (await h.install()).frozen;
    await expectLater(h.workspace.readFrozenBaseline(h.store, f.id, 2),
        throwsA(isA<SegmentedException>()));
    expect(h.store.frozenGenerations().single.id, f.id);
  });
  test('T02 failed pin transaction rolls back all association rows', () async {
    sqlFault = (p) {
      if (p == 'after_frozen_prepare') throw StateError('synthetic full disk');
    };
    final previous = h.baselineFile.readAsBytesSync();
    await expectLater(h.install(), throwsA(isA<StateError>()));
    expect(h.store.frozenGenerations(), isEmpty);
    expect(h.baselineFile.readAsBytesSync(), previous);
    final d = sqlite3.open(h.store.path);
    expect(d.select('PRAGMA foreign_key_check'), isEmpty);
    d.close();
  });
  test('T02 schema upgrade is opt-in and old publication handles refuse v5',
      () async {
    await h.install();
    expect(
        () =>
            SegmentedClientStore.open(h.root, h.store.cache, publication: true),
        throwsA(isA<SegmentedException>()));
    final d = sqlite3.open(h.store.path);
    expect(d.select('PRAGMA user_version').single.values.first, 5);
    d.close();
  });
  test('T02 valid v4 upgrade preserves immutable objects and original triggers',
      () {
    final root = Directory('${h.root.path}/upgrade')..createSync();
    final cache = h.store.cache;
    var store = SegmentedClientStore.open(root, cache, publication: true);
    final path = store.path;
    final fixture = GenerationFixture(bridge.fixture),
        ref = GenerationFixture(bridge.fixture).target.roots['raw']!;
    store.putVerifiedObject(ref, fixture.objects[ref.hash]!);
    store.close();
    final before = sqlite3.open(path);
    final oldTriggers = before
        .select("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
        .map((r) => [r['name'], r['sql']])
        .toList();
    expect(before.select('PRAGMA user_version').single.values.first, 4);
    before.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    expect(store.getVerifiedObject(ref), isNotNull);
    final after = sqlite3.open(path);
    expect(
        after.select(
            'SELECT body FROM objects WHERE hash=?', [ref.hash]).single['body'],
        fixture.objects[ref.hash]);
    for (final t in oldTriggers) {
      expect(
          after.select('SELECT sql FROM sqlite_master WHERE name=?',
              [t[0]]).single['sql'],
          t[1]);
    }
    expect(after.select('PRAGMA user_version').single.values.first, 5);
    expect(after.select('PRAGMA foreign_key_check'), isEmpty);
    after.close();
    store.close();
  });
  test('T02 damaged v4 cannot be repaired by opt-in upgrade', () {
    final root = Directory('${h.root.path}/damaged-upgrade')..createSync();
    final cache = h.store.cache;
    final store = SegmentedClientStore.open(root, cache, publication: true);
    final path = store.path;
    store.close();
    final d = sqlite3.open(path);
    d.execute('DROP TRIGGER immutable_body');
    expect(() => SegmentedClientStore.open(root, cache, adapters: true),
        throwsA(isA<SegmentedException>()));
    expect(d.select('PRAGMA user_version').single.values.first, 4);
    expect(
        d.select("SELECT 1 FROM sqlite_master WHERE name='frozen'"), isEmpty);
    d.close();
  });
  test(
      'T02 actual SQLITE_BUSY leaves exact installed frozen association intact',
      () async {
    final f = (await h.install()).frozen;
    final before = closure(f.generationId);
    final d = sqlite3.open(h.store.path);
    d.execute('BEGIN IMMEDIATE');
    try {
      expect(
          () => h.store.finishFrozenHandoff(f, finalAuthorityFence: () {}),
          throwsA(isA<SegmentedException>().having(
              (e) => e.code, 'actual SQLite busy error', 'STORE_BUSY')));
    } finally {
      d.execute('ROLLBACK');
      d.close();
    }
    expect(closure(f.generationId), before);
    expect(h.store.frozenGenerations().single.checksum, f.checksum);
  });
  test('T02 asynchronous final fence is rejected before any pin transition',
      () async {
    final f = (await h.install()).frozen;
    var called = false;
    expect(
        () => h.store.finishFrozenHandoff(f, finalAuthorityFence: () async {
              called = true;
            }),
        throwsA(isA<SegmentedException>()));
    expect(called, false);
    expect(h.store.frozenGenerations().single.checksum, f.checksum);
  });
  test(
      'T02 explicit legacy replacement releases only obsolete ONLINE frozen association',
      () async {
    final first = (await h.install()).frozen;
    await bridge.command({'command': 'mutate'});
    final second = (await h.install()).frozen;
    expect(second.id, isNot(first.id));
    expect(h.store.frozenGenerations().map((f) => f.id), [second.id]);
    expect(h.store.acceptedGeneration().previousId, first.generationId);
  });
  test(
      'T02 active frozen J prevents replacement or rebase and retains exact bytes',
      () async {
    final f = (await h.install()).frozen;
    final b = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
    await h.workspace.saveMetadata(OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint: f.binding['legacy_lineage']));
    await h.workspace.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: {
          'occurred_on': '2026-10-14',
          'title': '원문',
          'amount_value': '+0007.00',
          'is_primary_income': 0
        },
        baseline: b);
    final file = File('${h.workspace.root.path}/offline-mode/journal.ndjson'),
        before = file.readAsBytesSync();
    await bridge.command({'command': 'mutate'});
    await expectLater(h.install(), throwsA(isA<SegmentedException>()));
    expect(file.readAsBytesSync(), before);
    expect(h.store.frozenGenerations().single.id, f.id);
  });
}
