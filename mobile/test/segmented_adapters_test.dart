@Timeout(Duration(minutes: 5))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/offline_mode_fixtures.dart';
import 'support/segmented_e2_fixture.dart';

class _NoOnlineBaselineRead extends OfflineStore {
  _NoOnlineBaselineRead(Directory root)
      : super(directoryProvider: () async => root);
  @override
  Future<OfflineBaseline?> loadBaseline() =>
      throw StateError('ONLINE must not scan B');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Map<String, dynamic> oracle;
  late GenerationFixture fixture;
  late Directory root;
  late SegmentedClientStore store;
  final user = baselineFixture().user;
  Matcher code(String value) =>
      throwsA(isA<SegmentedException>().having((e) => e.code, 'code', value));
  Future<void> publish([GenerationFixture? target]) async {
    final base = await store.recoverAcceptedGeneration();
    final acquired =
        await IncrementalFetcher(store, FixtureTransport(target ?? fixture))
            .acquire(verifiedBase: base);
    final version = store.publicationDataVersion;
    final proof = await store.verifyPublicationCandidate(
        acquired.manifest, base,
        verifiedDataVersion: version);
    final prepared = store.prepareGeneration(
        syncUuid(), acquired.stagingId, proof, base,
        verifiedDataVersion: version);
    store.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
  }

  setUpAll(() async {
    final repo = Directory.current.parent.path;
    final result = await Process.run('$repo/.venv/bin/python',
        ['$repo/mobile/test/support/e4_backend_oracle.py']);
    expect(result.exitCode, 0, reason: result.stderr as String);
    oracle = jsonDecode(result.stdout as String) as Map<String, dynamic>;
    fixture = GenerationFixture(oracle['fixture']);
  });
  setUp(() async {
    root = Directory.systemTemp.createTempSync('mn-e4-adapter-');
    store = SegmentedClientStore.open(root, fixture.cache, publication: true);
    await publish();
  });
  tearDown(() {
    store.close();
    root.deleteSync(recursive: true);
  });

  test(
      'audited E3 accepted handoff preserves backend hot and separate identity',
      () {
    final accepted = store.acceptedGeneration();
    final view = store.withAcceptedRead(
        accepted, (read) => readSegmentedAuthority(read, user));
    expect(view.target.syncRoot, fixture.target.syncRoot);
    expect(view.generationId, accepted.id);
    expect(view.candidate.settings.values['cash_flow_balance'],
        '\u001c+0001000.00\u001f');
    expect(view.candidate.summary.cashFlowBalance,
        oracle['wire']['state']['summary']['cash_flow_balance']);
    expect(store.withAcceptedRead(accepted, (r) => r.hot['state']),
        oracle['wire']['state']);
    final direct = sqlite3.open(store.path);
    expect(
        direct.select('SELECT sequence FROM accepted').single['sequence'], 1);
    expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
    direct.close();
  });

  for (final table in segmentedTables) {
    test(
        'generation-bound primary-key page preserves actual backend $table rows',
        () {
      final expected = (fixture.source[table] as List).cast<Map>();
      final rows = store.withAcceptedRead(
          store.acceptedGeneration(), (r) => r.rows(table));
      expect(rows.length, expected.length);
      expect({for (final r in rows) r[primaryColumn(table)]: r},
          {for (final r in expected) r[primaryColumn(table)]: r});
      if (rows.isNotEmpty) {
        expect(() => rows.first['synthetic'] = true, throwsUnsupportedError);
      }
    });
  }
  test(
      'complete materialization matches independent backend manifest and original control',
      () async {
    final accepted = store.acceptedGeneration();
    final proof = await store.verifyAcceptedForMaterialization(accepted);
    final legacy = store.withAcceptedRead(
        accepted, (r) => materializeLegacyRead(r, user),
        materializationProof: proof);
    expect(legacy.envelope.snapshot, oracle['expected_snapshot']);
    expect(oracle['expected_restore_admission'], true);
    expect(legacy.envelope.fingerprint, oracle['expected_fingerprint']);
    expect(legacy.envelope.fingerprint, isNot(fixture.target.syncRoot));
    expect(legacy.candidate.settings.values['cash_flow_balance'],
        '\u001c+0001000.00\u001f');
    expect(() => exactMoney('\u001c+0001000.00\u001f'), throwsFormatException);
  });
  test('no full Snapshot from receipt/completion flag alone', () {
    expect(
        () => store.withAcceptedRead(
            store.acceptedGeneration(), (r) => materializeLegacyRead(r, user)),
        code('MATERIALIZATION_PROOF_REQUIRED'));
  });
  test('explicit legacy export budget fails without modifying accepted state',
      () async {
    final accepted = store.acceptedGeneration();
    final proof = await store.verifyAcceptedForMaterialization(accepted);
    expect(
        () => store.withAcceptedRead(
            accepted, (r) => materializeLegacyRead(r, user, maxBytes: 10),
            materializationProof: proof),
        code('LEGACY_MATERIALIZATION_BUDGET'));
    expect(store.acceptedGeneration().id, accepted.id);
  });
  test(
      'hot reads reuse healthy provenance, with zero full scans and pin writes',
      () async {
    final before = store.work.snapshot();
    for (var i = 0; i < 8; i++) {
      final accepted = await store.recoverAcceptedGeneration();
      store.withAcceptedRead(accepted, (r) => readSegmentedAuthority(r, user));
    }
    final work = store.work.since(before);
    expect(work['adapter_object_reads'], 16);
    for (final key in [
      'full_recoveries',
      'recovery_objects',
      'full_raw_rows',
      'full_fact_rows',
      'pin_inserts',
      'pin_deletes'
    ]) {
      expect(work[key] ?? 0, 0, reason: key);
    }
  });
  test('borrowed view cannot escape logical read scope', () {
    final view = store.withAcceptedRead(store.acceptedGeneration(), (r) => r);
    expect(() => view.hot, code('ACCEPTED_READ_CLOSED'));
    expect(() => view.rows('ledger_entries'), code('ACCEPTED_READ_CLOSED'));
  });
  test('async callback rejected before owning native snapshot', () {
    expect(
        () => store.withAcceptedRead(
            store.acceptedGeneration(), (r) async => r.hot),
        code('ASYNC_ACCEPTED_READ'));
    store.withAcceptedRead(store.acceptedGeneration(), (r) => r.hot);
  });
  test('same-connection write rejected without rolling back reader snapshot',
      () {
    store.withAcceptedRead(store.acceptedGeneration(), (read) {
      expect(() => store.removeUnreferencedStagingData(syncUuid()),
          code('ACCEPTED_READ_IN_PROGRESS'));
      expect(() => store.close(), code('ACCEPTED_READ_IN_PROGRESS'));
      expect(read.hot['kind'], 'hot');
    });
  });
  test(
      'another connection cannot COMMIT while snapshot owns roots; release restores writer',
      () {
    final other = sqlite3.open(store.path);
    other.execute('PRAGMA busy_timeout=1');
    final accepted = store.acceptedGeneration();
    store.withAcceptedRead(accepted, (r) {
      other.execute('BEGIN IMMEDIATE');
      other.execute('UPDATE accepted SET sequence=sequence WHERE id=1');
      expect(() => other.execute('COMMIT'), throwsA(isA<SqliteException>()));
      other.execute('ROLLBACK');
      expect(readSegmentedAuthority(r, user).target.syncRoot,
          fixture.target.syncRoot);
    });
    other.execute('BEGIN IMMEDIATE');
    other.execute('UPDATE accepted SET sequence=sequence WHERE id=1');
    other.execute('COMMIT');
    expect(other.select('SELECT sequence FROM accepted').single['sequence'], 1);
    other.close();
  });
  test('callback failure releases reader and preserves primary error', () {
    final failure = StateError('synthetic read failure');
    expect(
        () => store.withAcceptedRead(
            store.acceptedGeneration(), (_) => throw failure),
        throwsA(same(failure)));
    store.withAcceptedRead(store.acceptedGeneration(), (r) => r.hot);
  });
  test('wrong current principal rejected', () {
    final wrong = AuthUser(
        id: user.id + 1,
        username: 'synthetic-other',
        displayName: '합성',
        sharePinNeedsChange: false);
    expect(
        () => store.withAcceptedRead(store.acceptedGeneration(),
            (r) => readSegmentedAuthority(r, wrong)),
        code('READ_PRINCIPAL_MISMATCH'));
  });
  test(
      'fresh reopen performs required recovery and retains raw read capability',
      () async {
    final id = store.acceptedGeneration().id;
    store.close();
    store = SegmentedClientStore.open(root, fixture.cache, publication: true);
    final accepted = await store.recoverAcceptedGeneration();
    expect(accepted.id, id);
    expect(store.withAcceptedRead(accepted, (r) => r.rows('app_settings')),
        isNotEmpty);
  });
  test(
      'external commit invalidates read provenance, explicit recovery restores it',
      () async {
    final expected = store.acceptedGeneration();
    final other =
        SegmentedClientStore.open(root, fixture.cache, publication: true);
    other.createStaging(syncUuid(), expected.manifest!, DateTime.now().toUtc());
    other.close();
    expect(() => store.withAcceptedRead(expected, (r) => r.hot),
        code('ACCEPTED_READ_STALE'));
    final recovered = await store.recoverAcceptedGeneration();
    store.withAcceptedRead(recovered, (r) => r.hot);
  });
  test('R1 gate has no flag or accepted-state bypass', () {
    expect(
        requireSegmentedOfflineRecovery, code('R1_RECOVERY_CONTRACT_REQUIRED'));
    store.withAcceptedRead(store.acceptedGeneration(), (r) => r.hot);
    expect(
        requireSegmentedOfflineRecovery, code('R1_RECOVERY_CONTRACT_REQUIRED'));
  });
  for (final query in [
    ('bad', 1),
    ('ledger_entries', 0),
    ('ledger_entries', 257)
  ]) {
    test('invalid bounded query ${query.$1}/${query.$2}', () {
      expect(
          () => store.withAcceptedRead(store.acceptedGeneration(),
              (r) => r.rows(query.$1, limit: query.$2)),
          code('READ_QUERY_INVALID'));
    });
  }

  test('frozen B/J is presented separately and remains byte-identical',
      () async {
    final legacy = OfflineStore(directoryProvider: () async => root);
    final b = baselineFixture();
    await legacy.replaceBaseline(b);
    await legacy.saveMetadata(OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint: legacy.recoveryLineageFingerprint(b)));
    await legacy.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: {
          'occurred_on': '2026-10-14',
          'title': '합성 😀',
          'amount_value': '+0007.00',
          'is_primary_income': 0
        },
        baseline: b);
    final files =
        Directory('${root.path}/offline-mode').listSync().whereType<File>();
    final before = {for (final f in files) f.path: f.readAsBytesSync()};
    final pending = (await readPendingLegacyView(legacy, user.id))!;
    expect(
        pending.bundle.operations.single.payload['amount_value'], '+0007.00');
    expect(pending.projection!.cashFlows.last.isOfflinePending, true);
    expect(pending.lineage, legacy.recoveryLineageFingerprint(b));
    expect(pending.bundle.baseline.serverStateFingerprint,
        b.serverStateFingerprint);
    for (final e in before.entries) {
      expect(File(e.key).readAsBytesSync(), e.value);
    }
    expect(store.acceptedGeneration().sequence, 1);
  });
  test('orphan J without B fails closed, never empty authoritative fallback',
      () async {
    final legacy = OfflineStore(directoryProvider: () async => root);
    final folder = Directory('${root.path}/offline-mode')..createSync();
    File('${folder.path}/journal.ndjson').writeAsStringSync(
        '${jsonEncode(OfflineJournalOperation(operationId: 'orphan', type: OfflineOperationType.createCashFlow, payload: {
              'amount_value': 1
            }, createdAt: DateTime.utc(2026), sequence: 1).toJson())}\n');
    await expectLater(readPendingLegacyView(legacy, user.id),
        code('LEGACY_LINEAGE_UNAVAILABLE'));
  });

  test(
      'G1 logical read serializes G2 publication; detached G1 and new G2 never mix',
      () async {
    final g1 = store.acceptedGeneration();
    final target = mutateGraph(fixture, 'control', (b) {
      b['exported_at'] = '2026-10-05T01:02:03Z';
    });
    final acquired = await IncrementalFetcher(store, FixtureTransport(target))
        .acquire(verifiedBase: g1);
    final version = store.publicationDataVersion;
    final proof = await store.verifyPublicationCandidate(acquired.manifest, g1,
        verifiedDataVersion: version);
    final prepared = store.prepareGeneration(
        syncUuid(), acquired.stagingId, proof, g1,
        verifiedDataVersion: version);
    final old = store.withAcceptedRead(g1, (r) {
      final control = r.control;
      expect(
          () => store.commitPreparedGeneration(prepared,
              finalAuthorityFence: () {}),
          code('ACCEPTED_READ_IN_PROGRESS'));
      expect(r.generation.id, g1.id);
      expect(r.control, control);
      return control;
    });
    store.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
    final g2 = store.acceptedGeneration();
    expect(g2.sequence, g1.sequence + 1);
    final next = store.withAcceptedRead(g2, (r) => r.control);
    expect(next['exported_at'], '2026-10-05T01:02:03Z');
    expect(old['exported_at'], isNot(next['exported_at']));
    expect(() => store.withAcceptedRead(g1, (r) => r.hot),
        code('ACCEPTED_READ_STALE'));
  });

  for (final damage in [
    'pointer',
    'receipt',
    'manifest',
    'schema',
    'hot',
    'missing-leaf'
  ]) {
    test(
        'independent SQLite $damage damage fails closed, preserves legacy bytes',
        () async {
      final accepted = store.acceptedGeneration();
      final legacy = OfflineStore(directoryProvider: () async => root);
      await legacy.replaceBaseline(baselineFixture());
      final file = File('${root.path}/offline-mode/baseline.json'),
          before = file.readAsBytesSync();
      final direct = sqlite3.open(store.path);
      direct.execute('PRAGMA foreign_keys=OFF');
      final definitions = direct
          .select("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
          .map((r) => (r['name'] as String, r['sql'] as String))
          .toList();
      direct.execute('BEGIN IMMEDIATE');
      for (final d in definitions) {
        direct.execute('DROP TRIGGER "${d.$1}"');
      }
      switch (damage) {
        case 'pointer':
          direct.execute('UPDATE accepted SET checksum=?', ['0' * 64]);
        case 'receipt':
          direct.execute('UPDATE generations SET receipt_checksum=? WHERE id=?',
              ['0' * 64, accepted.id]);
        case 'manifest':
          direct.execute(
              'UPDATE generations SET manifest_checksum=? WHERE id=?',
              ['0' * 64, accepted.id]);
        case 'hot':
          final ref = fixture.target.roots['hot']!;
          final bytes = List<int>.from(fixture.objects[ref.hash]!);
          bytes[0] ^= 1;
          direct.execute(
              'UPDATE objects SET body=? WHERE hash=?', [bytes, ref.hash]);
        case 'missing-leaf':
          final leaf = fixture.objects.entries.firstWhere(
              (e) => (decodeC1(e.value) as Map)['kind'] == 'snapshot-leaf');
          direct.execute('DELETE FROM objects WHERE hash=?', [leaf.key]);
        case 'schema':
          break;
      }
      for (final (index, d) in definitions.indexed) {
        if (damage != 'schema' || index != 0) direct.execute(d.$2);
      }
      direct.execute('COMMIT');
      expect(
          direct.select('SELECT current_id FROM accepted').single['current_id'],
          accepted.id);
      direct.close();
      expect(() => store.withAcceptedRead(accepted, (r) => r.hot),
          throwsA(isA<SegmentedException>()));
      await expectLater(store.recoverAcceptedGeneration(),
          throwsA(isA<SegmentedException>()));
      expect(file.readAsBytesSync(), before);
    });
  }

  test(
      'empty authoritative tables keep genuine empty semantics and complete v7',
      () async {
    final repo = Directory.current.parent.path;
    final run = await Process.run('$repo/.venv/bin/python',
        ['$repo/mobile/test/support/e4_backend_oracle.py', '--empty']);
    expect(run.exitCode, 0, reason: run.stderr as String);
    final evidence = jsonDecode(run.stdout as String) as Map<String, dynamic>;
    final empty = GenerationFixture(evidence['fixture']);
    store.close();
    store = SegmentedClientStore.open(
        Directory('${root.path}/empty'), empty.cache,
        publication: true);
    await publish(empty);
    final a = store.acceptedGeneration();
    final proof = await store.verifyAcceptedForMaterialization(a);
    final legacy = store.withAcceptedRead(a, (r) {
      for (final table in segmentedTables
          .where((t) => t != 'app_settings' && t != 'app_labels')) {
        expect(r.rows(table), isEmpty);
      }
      return materializeLegacyRead(r, user);
    }, materializationProof: proof);
    expect(legacy.envelope.snapshot, evidence['expected_snapshot']);
    expect(legacy.candidate.entries, isEmpty);
    expect(legacy.candidate.cashFlows, isEmpty);
  });

  test('pending-heavy isolated view preserves synthetic J identities and bytes',
      () async {
    final legacy = OfflineStore(directoryProvider: () async => root),
        b = baselineFixture();
    await legacy.replaceBaseline(b);
    await legacy.saveMetadata(OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint: legacy.recoveryLineageFingerprint(b)));
    final journal = File('${root.path}/offline-mode/journal.ndjson');
    final operations = [
      for (var i = 1; i <= 128; i++)
        OfflineJournalOperation(
            operationId: 'e4-fixed-$i',
            sequence: i,
            createdAt: DateTime.utc(2026, 10, 14),
            type: OfflineOperationType.createCashFlow,
            payload: {
              'occurred_on': '2026-10-14',
              'title': '합성 😀 $i',
              'amount_value': '+0001.00',
              'is_primary_income': 0
            })
    ];
    journal.writeAsStringSync(
        '${operations.map((o) => jsonEncode(o.toJson())).join('\n')}\n',
        flush: true);
    final before = journal.readAsBytesSync();
    final view = (await readPendingLegacyView(legacy, user.id))!;
    expect(view.bundle.operations.map((o) => o.toJson()).toList(),
        operations.map((o) => o.toJson()).toList());
    expect(view.projection!.cashFlows.length, b.cashFlows.length + 128);
    expect(journal.readAsBytesSync(), before);
  });

  test(
      'large table materialization crosses 256-row page using exact typed string key',
      () async {
    final bridge = await BackendBridge.start(history: 300);
    try {
      final large = GenerationFixture(bridge.fixture);
      store.close();
      store = SegmentedClientStore.open(
          Directory('${root.path}/large'), large.cache,
          publication: true);
      await publish(large);
      final accepted = store.acceptedGeneration();
      final proof = await store.verifyAcceptedForMaterialization(accepted);
      final data = store.withAcceptedRead(
          accepted, (r) => r.materializationRows(),
          materializationProof: proof);
      for (final table in segmentedTables) {
        expect({
          for (final row in data[table]) row[primaryColumn(table)]: row
        }, {
          for (final row in large.source[table]) row[primaryColumn(table)]: row
        }, reason: table);
      }
      expect((data['ledger_entries'] as List).length, 301);
    } finally {
      await bridge.dispose();
    }
  });

  test(
      'ONLINE pending read neither materializes B nor manufactures frozen lineage',
      () async {
    final legacy = OfflineStore(directoryProvider: () async => root);
    await legacy.replaceBaseline(baselineFixture());
    final before =
        File('${root.path}/offline-mode/baseline.json').readAsBytesSync();
    expect(await readPendingLegacyView(_NoOnlineBaselineRead(root), user.id),
        null);
    expect(File('${root.path}/offline-mode/baseline.json').readAsBytesSync(),
        before);
  });

  test('finalizing pending read cannot rebind old J to a resolved baseline',
      () async {
    final legacy = OfflineStore(directoryProvider: () async => root);
    await legacy.replaceBaseline(baselineFixture());
    await legacy.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationFinalizing));
    await expectLater(readPendingLegacyView(legacy, user.id),
        code('LEGACY_LINEAGE_UNAVAILABLE'));
  });
}
