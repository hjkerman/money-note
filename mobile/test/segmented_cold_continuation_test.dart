@Timeout(Duration(minutes: 10))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../docs/benchmarks/t66f-b02-implementation/verification_profile.dart';
import 'support/segmented_e2_fixture.dart';
import 'support/segmented_large_transport.dart';

void main() {
  late GenerationFixture fixture;
  final evidence = <String, dynamic>{};
  setUpAll(() async {
    final bridge = await BackendBridge.start(history: 200);
    fixture = GenerationFixture(bridge.fixture);
    await bridge.dispose();
  });
  tearDownAll(() {
    final out = Platform.environment['B02_A02_CONTINUATION_OUT'];
    if (out != null) File(out).writeAsStringSync('${jsonEncode(evidence)}\n');
  });
  test('A02 approved exact three engines only, all other hashes rejected', () {
    final versions = fixture.target.versions;
    for (final hash in [
      ReleaseContract.financialEngine,
      ReleaseContract.previousFinancialEngine,
      ReleaseContract.historicalFinancialEngine,
      '0' * 64,
      'f' * 64
    ]) {
      final context = fixture.target.context.toJson()
        ..['financial_engine'] = hash;
      void check() => const ReleaseContract()
          .verify(versions, FinancialContext.parse(context));
      if (hash == '0' * 64 || hash == 'f' * 64) {
        expect(check, throwsA(isA<SegmentedException>()));
      } else {
        check();
      }
    }
  });
  test('A02 partial oversized object buffer is discarded across leases',
      () async {
    final bridge = await BackendBridge.start();
    final initial = GenerationFixture(bridge.fixture);
    await bridge.dispose();
    final big = mutateGraph(initial, 'snapshot-leaf', (body) {
      expect(body['table'], 'ledger_entries');
      expect((body['rows'] as List).length, 1);
      body['rows'][0]['value']['title'] = 'x' * 1100000;
      body['oversized'] = true;
    });
    // Only transport/typed closure is exercised, NOT F(raw)/E3 authority.
    final hash =
        big.objects.entries.singleWhere((e) => e.value.length > 1048576).key;
    final dir = Directory.systemTemp.createTempSync('mn-a02-chunks-');
    final store = SegmentedClientStore.open(dir, big.cache,
        publication: true, limits: largeVerificationStoreLimits);
    final transport = BatchFixtureTransport(big);
    final offsets = <String, List<String>>{};
    var expired = false;
    transport.before = (method, path, body) async {
      if (!path.endsWith('/objects')) return null;
      final items = body!['items'] as List;
      if (items.length == 1 && (items.single['path'] as List).last == hash) {
        final offset = items.single['offset'] as String;
        offsets.putIfAbsent(path, () => []).add(offset);
        if (!expired && offset != '0') {
          expired = true;
          return remoteError('OBSERVATION_EXPIRED', 'new_observation', 410,
              body['request_id']);
        }
      }
      return null;
    };
    try {
      final acquired = await IncrementalFetcher(store, transport,
              limits: largeVerificationFetchLimits)
          .acquire();
      expect(acquired.graph.objects.map((r) => r.hash).toSet(),
          big.objects.keys.toSet());
      expect(expired, true);
      expect(offsets.length, 2);
      expect(offsets.values.every((v) => v.first == '0'), true);
      final db = sqlite3.open(store.path);
      try {
        expect(
            db.select(
                'SELECT body FROM objects WHERE hash=?', [hash]).single['body'],
            big.objects[hash]);
        expect(
            db.select('SELECT current_id FROM accepted').single['current_id'],
            isNull);
        expect(db.select('PRAGMA foreign_key_check'), isEmpty);
      } finally {
        db.close();
      }
    } finally {
      store.close();
      dir.deleteSync(recursive: true);
    }
  });
  for (final mode in [
    'control',
    'packet',
    'twice',
    'terminal',
    'terminal-twice',
    'exhausted',
    'changed-target',
    'wrong-principal',
    'wrong-epoch',
    'cancel',
    'logout',
    'external-commit',
    'external-corruption',
    'missing-trigger',
    'stage-failure'
  ]) {
    test('A02 cold continuation: $mode', () async {
      final dir = Directory.systemTemp.createTempSync('mn-a02-continuation-');
      var failStage = false;
      final store = SegmentedClientStore.open(dir, fixture.cache,
          publication: true, limits: largeVerificationStoreLimits, fault: (p) {
        if (failStage && p == 'after_staging_insert') {
          throw StateError('synthetic stage failure');
        }
      });
      final transport = BatchFixtureTransport(fixture),
          cancel = SyncCancellation();
      var injected = 0, packetCalls = 0;
      final maxRenewals = mode.contains('twice') ? 2 : 1;
      var expected = fixture;
      final start = Stopwatch()..start();
      final snapshots = <Map<String, Object?>>[];
      transport.before = (method, path, body) async {
        if (method == 'DELETE') return null;
        final terminal = path.endsWith('/observations') &&
            transport.observations.containsKey(body?['request_id']);
        if (path.endsWith('/objects')) packetCalls++;
        final expire = mode == 'exhausted'
            ? path.endsWith('/objects')
            : mode.startsWith('terminal')
                ? terminal
                : path.endsWith('/objects') && packetCalls >= 5 + injected * 5;
        if (mode == 'control' ||
            !expire ||
            (mode != 'exhausted' && injected >= maxRenewals)) {
          return null;
        }
        injected++;
        snapshots.add({
          'time_us': start.elapsedMicroseconds,
          'work': store.work.snapshot(),
          'requests': transport.objectRequests
        });
        if (mode == 'changed-target') {
          // Equal roots alone are insufficient: exact Target revision differs.
          final target = fixture.target.toJson()..remove('sync_root');
          target['revision'] = '${int.parse(target['revision']) + 1}';
          target['sync_root'] = objectHash('view', encodeC1(target));
          expected = GenerationFixture({
            'manifest': {...fixture.manifest, 'target': target},
            'objects': [
              for (final e in fixture.objects.entries)
                {
                  'ref': {'hash': e.key, 'bytes': '${e.value.length}'},
                  'data_base64': base64Encode(e.value)
                }
            ],
            'rows': fixture.rows,
            'source': fixture.source
          });
          transport.fixture = expected;
        }
        if (mode == 'wrong-principal' || mode == 'wrong-epoch') {
          final target = fixture.target.toJson()..remove('sync_root');
          if (mode == 'wrong-principal') {
            target['principal_id'] = 2;
          } else {
            target['ns']['epoch'] = syncUuid();
          }
          target['sync_root'] = objectHash('view', encodeC1(target));
          transport.fixture = GenerationFixture({
            'manifest': {...fixture.manifest, 'target': target},
            'objects': [],
            'rows': fixture.rows,
            'source': fixture.source
          });
        }
        if (mode == 'cancel') cancel.cancel();
        if (mode == 'logout') transport.authenticated = false;
        if (mode.startsWith('external-') || mode == 'missing-trigger') {
          final db = sqlite3.open(store.path);
          try {
            if (mode == 'external-commit') {
              db.execute('CREATE TABLE a02_external_change(n)');
            } else {
              final trigger = db
                  .select(
                      "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='objects'")
                  .first['name'];
              db.execute('DROP TRIGGER "$trigger"');
              if (mode == 'external-corruption') {
                // Remove remaining object update guards only in this disposable DB.
                for (final row in db.select(
                    "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='objects'")) {
                  db.execute('DROP TRIGGER "${row['name']}"');
                }
                db.execute(
                    "UPDATE objects SET body=X'7b7d' WHERE hash=(SELECT hash FROM objects LIMIT 1)");
              }
            }
          } finally {
            db.close();
          }
        }
        if (mode == 'stage-failure') failStage = true;
        return remoteError('OBSERVATION_EXPIRED', 'new_observation', 410,
            body!['request_id'] as String);
      };
      try {
        final failures = {
          'exhausted': 'OBSERVATION_EXPIRED',
          'wrong-principal': 'CACHE_CONTEXT_MISMATCH',
          'wrong-epoch': 'CACHE_CONTEXT_MISMATCH',
          'cancel': 'ACQUISITION_CANCELLED',
          'logout': 'AUTHENTICATION_CHANGED',
          'external-commit': 'VERIFICATION_STALE',
          'external-corruption': 'VERIFICATION_STALE',
          'missing-trigger': 'VERIFICATION_STALE',
          'stage-failure': 'ACQUISITION_FAILED'
        };
        final future = IncrementalFetcher(store, transport,
                limits: largeVerificationFetchLimits)
            .acquire(cancellation: cancel);
        if (failures.containsKey(mode)) {
          await expectLater(
              future,
              throwsA(isA<AcquisitionFailure>()
                  .having((e) => e.code, 'code', failures[mode])));
        } else {
          final result = await future;
          expect(result.graph.objects.map((r) => r.hash).toSet(),
              expected.objects.keys.toSet());
          expect(result.manifest.target.syncRoot, expected.target.syncRoot);
          expect(store.acquisitionProgress(result.stagingId)!.state,
              'graph_verified');
          if (mode != 'changed-target') {
            expect(store.work.snapshot()['graph_nodes_examined'],
                fixture.objects.length);
          } else {
            expect(store.work.snapshot()['cold_changed_target_restarts'], 1);
          }
          if (mode == 'terminal' || mode == 'terminal-twice') {
            expect(result.manifest.id,
                isNot(transport.observations.values.first['observation_id']));
          }
        }
        final db = sqlite3.open(store.path);
        try {
          expect(
              db
                  .select(
                      'SELECT current_id,previous_id,sequence FROM accepted')
                  .single['current_id'],
              isNull);
          expect(db.select('SELECT count(*) AS n FROM generations').single['n'],
              0);
          if (!mode.startsWith('external-') && mode != 'missing-trigger') {
            expect(db.select('PRAGMA foreign_key_check'), isEmpty);
            for (final row in db.select('SELECT hash,body FROM objects')) {
              expect(
                  row['body'],
                  expected.objects[row['hash']] ??
                      fixture.objects[row['hash']]);
            }
          }
          expect(transport.observations.length, lessThanOrEqualTo(3));
          evidence[mode] = {
            'injected': injected,
            'observations': transport.observations.length,
            'elapsed_us': start.elapsedMicroseconds,
            'work': store.work.snapshot(),
            'snapshots': snapshots,
            'downloaded_hashes': transport.requestedHashes.toSet().length,
            'durable_objects':
                db.select('SELECT count(*) AS n FROM objects').single['n']
          };
        } finally {
          db.close();
        }
      } finally {
        store.close();
        dir.deleteSync(recursive: true);
      }
    });
  }
}
