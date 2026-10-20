@Timeout(Duration(minutes: 15))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../docs/benchmarks/t66f-b02-a01-correction/before_fetch.dart'
    as before;
import '../../docs/benchmarks/t66f-b02-a01-correction/failed_cursor_fetch.dart'
    as failed;
import '../../docs/benchmarks/t66f-b02-implementation/verification_profile.dart';
import 'support/segmented_e2_fixture.dart';
import 'support/segmented_large_transport.dart';

void main() {
  final evidence = <String, dynamic>{};
  tearDownAll(() {
    final out = Platform.environment['B02_A01_PACKET_OUT'];
    if (out != null) {
      File(out).writeAsStringSync(
          '${const JsonEncoder.withIndent('  ').convert(evidence)}\n');
    }
  });
  for (final n in [0, 200, 1000]) {
    late GenerationFixture fixture;
    setUpAll(() async {
      final bridge = await BackendBridge.start(history: n);
      fixture = GenerationFixture(bridge.fixture);
      await bridge.dispose();
    });
    Future<Map<String, dynamic>> run(bool old, bool cached,
        {bool parentsOnly = false, bool failedCursor = false}) async {
      final dir = Directory.systemTemp.createTempSync('mn-a01-packet-');
      final store = SegmentedClientStore.open(dir, fixture.cache,
          publication: true, limits: largeVerificationStoreLimits);
      final transport = BatchFixtureTransport(fixture);
      var turns = 0;
      final timer = Timer.periodic(const Duration(milliseconds: 1), (_) {
        turns++;
      });
      try {
        var preloaded = 0;
        if (cached || parentsOnly) {
          // Fixture preparation, outside timing. Reuse the actual bounded E1
          // batch instead of thousands of unrelated single-object commits.
          final stage = syncUuid();
          store.createStaging(
              stage,
              ObservationManifest.fromBytes(encodeC1(fixture.manifest)),
              DateTime.now().toUtc());
          final batch = <({ObjectRef ref, List<int>? bytes})>[];
          var size = 0;
          for (final entry in fixture.objects.entries) {
            if (parentsOnly &&
                !{'raw-root', 'snapshot-node', 'index-root', 'index-node'}
                    .contains((decodeC1(entry.value) as Map)['kind'])) {
              continue;
            }
            final ref = ObjectRef.parse(
                {'hash': entry.key, 'bytes': '${entry.value.length}'});
            if (batch.isNotEmpty &&
                (batch.length == 64 || size + entry.value.length > 1048576)) {
              store.putVerifiedStagedBatch(stage, batch);
              batch.clear();
              size = 0;
            }
            batch.add((ref: ref, bytes: entry.value));
            size += entry.value.length;
            preloaded++;
          }
          if (batch.isNotEmpty) store.putVerifiedStagedBatch(stage, batch);
        }
        if (failedCursor) {
          await expectLater(
              failed.IncrementalFetcher(store, transport,
                      limits: const failed.FetchLimits.largeGraphVerification())
                  .acquire(),
              throwsA(isA<failed.AcquisitionFailure>()
                  .having((e) => e.code, 'code', 'GRAPH_DEPTH_BUDGET')));
          expect(transport.objectRequests, 0);
          final db = sqlite3.open(store.path);
          try {
            expect(db.select('SELECT count(*) AS n FROM objects').single['n'],
                preloaded);
            expect(
                db
                    .select('SELECT current_id FROM accepted')
                    .single['current_id'],
                isNull);
          } finally {
            db.close();
          }
          return {
            'failure': 'GRAPH_DEPTH_BUDGET',
            'preloaded': preloaded,
            'http_objects': 0,
            'injected_cursor_count_cap': 16,
            'unchanged_real_path_cap': 512
          };
        }
        final start = Stopwatch()..start();
        final dynamic result = old
            ? await before.IncrementalFetcher(store, transport,
                    limits: const before.FetchLimits.largeGraphVerification())
                .acquire()
            : await IncrementalFetcher(store, transport,
                    limits: largeVerificationFetchLimits)
                .acquire();
        final packets = [
          for (final b in transport.bodies)
            if (b.containsKey('items')) (b['items'] as List).length
        ];
        expect(result.graph.objects.map((dynamic r) => r.hash).toSet(),
            fixture.objects.keys.toSet());
        expect(transport.requestedHashes.toSet().length,
            transport.requestedHashes.length);
        expect(result.metrics.downloadedObjects,
            fixture.objects.length - preloaded);
        for (final body
            in transport.bodies.where((b) => b.containsKey('items'))) {
          final items = body['items'] as List;
          expect(items.length, inInclusiveRange(1, 64));
          expect(items.fold<int>(0, (s, i) => s + (i['length'] as int)),
              lessThanOrEqualTo(1048576));
          for (final i in items) {
            final path = i['path'] as List;
            expect(path.length, lessThanOrEqualTo(512));
            // The real server checks typed membership; here every hop exists
            // in the independent backend-generated immutable fixture.
            expect(path.every(fixture.objects.containsKey), true);
          }
        }
        final db = sqlite3.open(store.path);
        try {
          expect(db.select('PRAGMA foreign_key_check'), isEmpty);
          expect(
              db
                  .select(
                      'SELECT count(*) AS n FROM accepted WHERE current_id IS NOT NULL')
                  .single['n'],
              0);
          expect(db.select('SELECT count(*) AS n FROM objects').single['n'],
              fixture.objects.length);
          for (final row in db.select('SELECT hash,body FROM objects')) {
            expect(row['body'], fixture.objects[row['hash']]);
          }
        } finally {
          db.close();
        }
        return {
          'objects': fixture.objects.length,
          'cached': cached,
          'packet_count': packets.length,
          'packet_histogram': {
            for (final size in packets.toSet())
              '$size': packets.where((p) => p == size).length
          },
          'average_items': packets.isEmpty
              ? 0
              : transport.requestedHashes.length / packets.length,
          'event_loop_turns': turns,
          'wall_us': start.elapsedMicroseconds,
          'rss_bytes': ProcessInfo.currentRss,
          'work': store.work.snapshot(),
          'metrics': result.metrics.toJson()
        };
      } finally {
        timer.cancel();
        store.close();
        dir.deleteSync(recursive: true);
      }
    }

    test('A01 same backend graph $n exact before/after cold packet oracle',
        () async {
      final a = await run(true, false), b = await run(false, false);
      evidence['cold_$n'] = {'before': a, 'after': b};
      if (n >= 200) {
        expect(b['packet_count'], lessThan(a['packet_count'] as int));
        expect(b['average_items'], greaterThan(a['average_items'] as double));
      }
      expect(b['event_loop_turns'], greaterThan(0));
    });
    test('A01 cached same graph $n yields with no object transfer', () async {
      final a = await run(true, true), b = await run(false, true);
      evidence['cached_$n'] = {'before': a, 'after': b};
      expect(b['packet_count'], 0);
      expect(b['event_loop_turns'], greaterThan(0));
      final work = b['work'] as Map;
      expect(work['cold_prefetch_cursors_enqueued'] ?? 0, 0);
      expect(work['cold_cached_parent_peak_sum'], lessThanOrEqualTo(512));
    });
    if (n == 1000) {
      test(
          'A01 compact count injection reproduces failed large cached cursor revision',
          () async {
        evidence['failed_cursor_compact'] =
            await run(false, true, failedCursor: true);
      });
      test('A01 cached internal parents still fill bounded leaf packets',
          () async {
        final a = await run(true, false, parentsOnly: true);
        final b = await run(false, false, parentsOnly: true);
        evidence['cached_parents_$n'] = {'before': a, 'after': b};
        expect(b['packet_count'], lessThan(a['packet_count'] as int));
        expect((b['work'] as Map)['cold_cached_parent_peak_sum'],
            lessThanOrEqualTo(512));
      });
    }
  }

  for (final scenario in ['cancel', 'session', 'expiry', 'renew_different']) {
    test('A01 cold yield/renewal $scenario keeps staged graph unpublished',
        () async {
      final bridge = await BackendBridge.start(history: 200);
      final fixture = GenerationFixture(bridge.fixture);
      await bridge.dispose();
      final dir = Directory.systemTemp.createTempSync('mn-a01-yield-');
      var store = SegmentedClientStore.open(dir, fixture.cache,
          publication: true, limits: largeVerificationStoreLimits);
      final transport = BatchFixtureTransport(fixture),
          cancel = SyncCancellation();
      Timer? timer;
      var packets = 0;
      transport.before = (_, path, body) async {
        if (!path.endsWith('/objects')) return null;
        packets++;
        if (scenario == 'expiry' || scenario == 'renew_different') {
          if (packets % 4 == 0) {
            if (scenario == 'renew_different') {
              transport.fixture = mutateGraph(fixture, 'snapshot-leaf', (b) {
                ((b['rows'] as List).first['value'] as Map)['title'] =
                    'renewed';
              });
            }
            return remoteError('OBSERVATION_EXPIRED', 'new_observation', 410,
                body!['request_id']);
          }
        } else {
          timer ??= Timer(Duration.zero, () {
            if (scenario == 'cancel') cancel.cancel();
            if (scenario == 'session') transport.authenticated = false;
          });
        }
        return null;
      };
      try {
        await expectLater(
            IncrementalFetcher(store, transport,
                    limits: largeVerificationFetchLimits)
                .acquire(cancellation: cancel),
            throwsA(isA<AcquisitionFailure>()));
        expect(transport.manifestRequests, lessThanOrEqualTo(3));
        if (scenario == 'expiry' || scenario == 'renew_different') {
          expect(transport.manifestRequests, 3);
        } else {
          expect(packets, lessThan(fixture.objects.length));
        }
        store.close();
        store = SegmentedClientStore.open(dir, fixture.cache,
            publication: true, limits: largeVerificationStoreLimits);
        expect(store.inspectStoreHealth().healthy, true);
        final db = sqlite3.open(store.path);
        try {
          expect(
              db
                  .select(
                      'SELECT count(*) AS n FROM accepted WHERE current_id IS NOT NULL')
                  .single['n'],
              0);
          expect(db.select('PRAGMA foreign_key_check'), isEmpty);
        } finally {
          db.close();
        }
      } finally {
        timer?.cancel();
        store.close();
        dir.deleteSync(recursive: true);
      }
    });
  }
  for (final accepted in [true, false]) {
    test(
        'A01 exact artifact allow-list rejects every unapproved engine ($accepted)',
        () {
      final raw = {
        'evaluation_date': '2026-10-05',
        'timezone_offset_minutes': 540,
        'financial_engine':
            accepted ? ReleaseContract.historicalFinancialEngine : '0' * 64
      };
      final versions = SyncVersions.parse({
        'sync': 1,
        'canon': 1,
        'structural': 1,
        'snapshot': 7,
        'recurring_ownership': 1,
        'raw_schema': ReleaseContract.rawSchema,
        'projection_schema': ReleaseContract.projectionSchema,
        'policy_registry': ReleaseContract.policyRegistry
      });
      void act() =>
          const ReleaseContract().verify(versions, FinancialContext.parse(raw));
      if (accepted) {
        act();
      } else {
        expect(act, throwsA(isA<SegmentedException>()));
      }
    });
  }
}
