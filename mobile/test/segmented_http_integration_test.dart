import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_e2_fixture.dart';

// Test-only reconstruction reads object bodies independently of E2 traversal.
void reconstruct(SegmentedClientStore store, VerifiedStagedGeneration result,
    Map<String, dynamic> oracle) {
  final expected = GenerationFixture(oracle);
  expect(result.graph.objects.map((r) => r.hash).toSet(),
      expected.objects.keys.toSet());
  final rows = <String, List<dynamic>>{}, facts = <dynamic>[];
  for (final ref in result.graph.objects) {
    final object = store.getVerifiedObject(ref)!;
    expect(object.bytes, expected.objects[ref.hash]);
    final b = object.body;
    if (object.kind == 'snapshot-leaf') {
      rows
          .putIfAbsent(b['table'] as String, () => [])
          .addAll(b['rows'] as List);
    }
    if (object.kind == 'index-leaf') facts.addAll(b['facts'] as List);
  }
  expect(rows.keys.toSet(), expected.source.keys.toSet());
  expect(rows.length, 11);
  for (final table in rows.keys) {
    final actual = rows[table]!, source = expected.source[table] as List;
    expect(actual.length, source.length);
    final byKey = {
      for (final row in actual) row['key'][1].toString(): row['value']
    };
    expect(
        byKey.length, actual.length); // independently detect duplicate/missing
    for (final row in source) {
      final key = (row['id'] ??
              row['key'] ??
              row['entry_payment_key'] ??
              row['registration_key'])
          .toString();
      expect(byKey[key], row, reason: table);
    }
  }
  // Canonical Patricia reconstructed independently from downloaded facts.
  final root =
      store.getVerifiedObject(result.manifest.target.roots['index']!)!.body;
  final common = {
    for (final field in ['ns', 'canon', 'raw_schema', 'structural'])
      field: root[field]
  };
  String bits(String h) => [
        for (var i = 0; i < h.length; i++)
          int.parse(h[i], radix: 16).toRadixString(2).padLeft(4, '0')
      ].join();
  Map<String, dynamic> make(String kind, Map<String, dynamic> values) {
    final raw = encodeC1({'kind': kind, ...common, ...values});
    return {'hash': objectHash(kind, raw), 'bytes': '${raw.length}'};
  }

  final groups = <String, List<dynamic>>{};
  for (final fact in facts) {
    groups
        .putIfAbsent(objectHash('fact-key', encodeC1(fact['key'])), () => [])
        .add(fact);
  }
  Map<String, dynamic> build(List<String> keys) {
    if (keys.isEmpty) return make('index-empty', {'count': '0'});
    if (keys.length == 1) {
      final group = groups[keys.single]!;
      group.sort((a, b) => byteCompare(encodeC1(a['key']), encodeC1(b['key'])));
      return make('index-leaf',
          {'count': '${group.length}', 'digest': keys.single, 'facts': group});
    }
    final first = bits(keys.first), last = bits(keys.last);
    var n = 0;
    while (first[n] == last[n]) {
      n++;
    }
    final left = keys.where((k) => bits(k)[n] == '0').toList(),
        right = keys.where((k) => bits(k)[n] == '1').toList();
    return make('index-node', {
      'count': '${keys.fold<int>(0, (n, k) => n + groups[k]!.length)}',
      'prefix': first.substring(0, n),
      'left': build(left),
      'right': build(right)
    });
  }

  final ordered = groups.keys.toList()..sort();
  final factsRef = build(ordered);
  expect(make('index-root', {'count': '${facts.length}', 'facts': factsRef}),
      result.manifest.target.roots['index']!.toJson());
}

void main() {
  test(
      'actual D3a/D3b: cold/identical/incremental/restart/resume + independent eleven-table oracle',
      () async {
    final bridge = await BackendBridge.start(history: 260);
    final fixture = GenerationFixture(bridge.fixture),
        root = Directory.systemTemp.createTempSync('money-note-e2-http-');
    var store =
        SegmentedClientStore.open(root, fixture.cache, acquisition: true);
    final transport = AuthenticatedSegmentedTransport(
        client: bridge,
        origin: syntheticOrigin,
        credential: () => bridge.token);
    IncrementalFetcher fetch() =>
        IncrementalFetcher(store, transport, delay: (_, c) async {
          c.check();
        });
    final measurements = <String, dynamic>{};
    try {
      final cold = await fetch().acquire();
      reconstruct(store, cold, await bridge.command({'command': 'oracle'}));
      measurements['cold'] = cold.metrics.toJson();
      final count = bridge.objectRequests;
      final repeated = await fetch().acquire();
      expect(bridge.objectRequests - count, 0);
      expect(repeated.metrics.objectRequests, 0);
      measurements['identical'] = repeated.metrics.toJson();
      await bridge.command({'command': 'mutate'});
      Map<String, dynamic>? observedBeforeWriter;
      bridge.before = (path) async {
        if (path.endsWith('/objects') && observedBeforeWriter == null) {
          // Capture direct source oracle for T, then COMMIT U while T's
          // observation remains valid. All subsequent paths must stay on T.
          observedBeforeWriter = await bridge.command({'command': 'oracle'});
          await bridge.command({'command': 'mutate'});
        }
      };
      final changed = await fetch().acquire();
      bridge.before = null;
      reconstruct(store, changed, observedBeforeWriter!);
      final latest = await bridge.command({'command': 'oracle'});
      expect(BigInt.parse(changed.manifest.target.revision),
          lessThan(BigInt.from(latest['revision'] as int)));
      final old = cold.graph.objects.map((r) => r.hash).toSet(),
          next = changed.graph.objects.map((r) => r.hash).toSet();
      expect(changed.metrics.downloadedObjects, next.difference(old).length);
      expect(changed.metrics.cacheHits, greaterThan(0));
      expect(changed.metrics.downloadedObjects,
          lessThan(cold.metrics.downloadedObjects));
      expect(changed.manifest.target.syncRoot,
          isNot(cold.manifest.target.syncRoot));
      measurements['incremental'] = changed.metrics.toJson();
      await bridge.command({'command': 'mutate'});
      final cancellation = SyncCancellation();
      var transferred = 0;
      bridge.before = (path) async {
        if (path.endsWith('/objects') && transferred++ == 2) {
          cancellation.cancel();
        }
      };
      String? resumeId;
      try {
        await fetch().acquire(cancellation: cancellation);
        fail('must cancel');
      } on AcquisitionFailure catch (e) {
        expect(e.code, 'ACQUISITION_CANCELLED');
        resumeId = e.stagingId;
      }
      expect(store.acquisitionProgress(resumeId!)!.state, 'interrupted');
      bridge.before = null;
      store.close();
      store = SegmentedClientStore.open(root, fixture.cache, acquisition: true);
      final resumed = await fetch().acquire(resumeId: resumeId);
      reconstruct(store, resumed, await bridge.command({'command': 'oracle'}));
      measurements['resumed'] = resumed.metrics.toJson();
      final direct = sqlite3.open(store.path);
      expect(direct.select('PRAGMA integrity_check').single.values.first, 'ok');
      expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
      expect(
          direct.select(
              "SELECT name FROM sqlite_master WHERE name IN ('active','accepted','generations')"),
          isEmpty);
      measurements['staging_logical_metadata_bytes'] =
          direct.select('SELECT metadata FROM usage').single['metadata'];
      direct.close();
      // Explicit opt-in output, no financial payloads or credential diagnostics.
      final output = Platform.environment['E2_BENCHMARK_OUTPUT'];
      if (output != null) {
        File(output).writeAsStringSync(
            '${const JsonEncoder.withIndent('  ').convert(measurements)}\n');
      }
      expect(await fetch().release(resumed.manifest.id), isTrue); // idempotent
    } finally {
      store.close();
      await bridge.dispose();
      root.deleteSync(recursive: true);
    }
  }, timeout: const Timeout(Duration(minutes: 12)));

  for (final mode in ['expired', 'revoked', 'wrong_token', 'typed_path']) {
    test('actual server $mode fails closed without active publication',
        () async {
      final bridge = await BackendBridge.start();
      final fixture = GenerationFixture(bridge.fixture),
          root = Directory.systemTemp.createTempSync('money-note-e2-auth-');
      final wrongToken = syncUuid();
      final store =
          SegmentedClientStore.open(root, fixture.cache, acquisition: true);
      final transport = AuthenticatedSegmentedTransport(
          client: bridge,
          origin: syntheticOrigin,
          credential: () => mode == 'wrong_token' ? wrongToken : bridge.token);
      try {
        if (mode == 'expired' || mode == 'revoked') {
          var injected = false;
          bridge.before = (path) async {
            if (path.endsWith('/objects') && !injected) {
              injected = true;
              await bridge.command(mode == 'expired'
                  ? {'command': 'advance', 'seconds': 901}
                  : {'command': 'revoke'});
            }
          };
        }
        if (mode == 'typed_path') {
          final reply = await transport.exchange(
              'POST',
              '/api/sync/v1/observations',
              encodeC1({
                'protocol': 1,
                'request_id': syncUuid(),
                'base': null,
                'inline_bytes': 0
              }),
              SyncCancellation(),
              8192);
          final m = ObservationManifest.fromBytes(reply.bytes);
          final nonce = syncUuid();
          final denied = await transport.exchange(
              'POST',
              '/api/sync/v1/observations/${m.id}/objects',
              encodeC1({
                'protocol': 1,
                'request_id': nonce,
                'items': [
                  {
                    'path': ['f' * 64],
                    'offset': '0',
                    'length': 1
                  }
                ]
              }),
              SyncCancellation(),
              8192);
          expect(denied.status, 422);
          expect(
              SyncRemoteException.parse(denied, nonce).code, 'INVALID_REQUEST');
          expect(store.listStoredObjectIdentities(), isEmpty);
        } else {
          final fetch =
              IncrementalFetcher(store, transport, delay: (_, c) async {
            c.check();
          });
          if (mode == 'expired') {
            final result = await fetch.acquire();
            expect(result.graph.objects.length, fixture.objects.length);
          } else {
            await expectLater(
                fetch.acquire(), throwsA(isA<AcquisitionFailure>()));
            expect(store.listStoredObjectIdentities(), isEmpty);
          }
        }
      } finally {
        store.close();
        await bridge.dispose();
        root.deleteSync(recursive: true);
      }
    }, timeout: const Timeout(Duration(minutes: 3)));
  }
}
