@Timeout(Duration(minutes: 5))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_e2_fixture.dart';
import 'support/offline_mode_fixtures.dart';

void main() {
  late Map<String, dynamic> fixture;
  late Map<String, dynamic> wire;
  setUpAll(() async {
    final repo = Directory.current.parent.path;
    final run = await Process.run('$repo/.venv/bin/python',
        ['$repo/mobile/test/support/e4_backend_oracle.py']);
    expect(run.exitCode, 0, reason: run.stderr as String);
    final evidence = jsonDecode(run.stdout as String) as Map<String, dynamic>;
    fixture = evidence['fixture'];
    wire = evidence['wire'];
  });
  for (final point in [
    'before_read',
    'during_read',
    'after_read',
    'full_proof_ready'
  ]) {
    test(
        'real E4 SIGKILL $point releases native snapshot, preserves accepted and legacy bytes',
        () async {
      final root = Directory.systemTemp.createTempSync('mn-e4-crash-');
      Process? child;
      SegmentedClientStore? store;
      try {
        final input = GenerationFixture(fixture);
        store = SegmentedClientStore.open(root, input.cache, publication: true);
        final expected = await store.recoverAcceptedGeneration();
        final acquired =
            await IncrementalFetcher(store, FixtureTransport(input)).acquire();
        final version = store.publicationDataVersion;
        final proof = await store.verifyPublicationCandidate(
            acquired.manifest, expected,
            verifiedDataVersion: version);
        final prepared = store.prepareGeneration(
            syncUuid(), acquired.stagingId, proof, expected,
            verifiedDataVersion: version);
        final publication = store.commitPreparedGeneration(prepared,
            finalAuthorityFence: () {});
        final path = store.path;
        store.close();
        store = null;
        File('${root.path}/e4-synthetic-owned').writeAsStringSync('E4 TEST');
        final legacyStore = OfflineStore(directoryProvider: () async => root);
        final baseline = OfflineBaseline.fromJson({
          ...wire['state'] as Map<String, dynamic>,
          'schema_version': 4,
          'synced_at': wire['snapshot']['exported_at'],
          'user': baselineFixture().toJson()['user'],
          'authoritative_snapshot': wire['snapshot'],
          'server_state_fingerprint': wire['authority']['state_fingerprint'],
          'resolved_reconciliation_id': null,
          'discount_policy_defaults': wire['authority']
              ['discount_policy_defaults']
        });
        await legacyStore.replaceBaseline(baseline);
        await legacyStore.saveMetadata(OfflineWorkspaceMetadata(
            mode: ConnectivityMode.offline,
            baselineLineageFingerprint:
                legacyStore.recoveryLineageFingerprint(baseline)));
        await legacyStore.appendOperation(
            type: OfflineOperationType.createCashFlow,
            payload: {
              'occurred_on': '2026-10-14',
              'title': '합성 😀',
              'amount_value': '+0007.00',
              'is_primary_income': 0
            },
            baseline: baseline);
        final legacy = Directory('${root.path}/offline-mode');
        final before = <String, List<int>>{};
        for (final f in legacy.listSync().whereType<File>()) {
          before[f.path] = f.readAsBytesSync();
        }
        File('${root.path}/synthetic-fixture.json')
            .writeAsStringSync(jsonEncode(fixture));
        child = await Process.start('/home/hjkerman/.flutter/bin/dart', [
          '--packages=.dart_tool/package_config.json',
          'test/support/segmented_read_crash_child.dart',
          root.path,
          point
        ]);
        final errors = StringBuffer();
        child.stderr.transform(utf8.decoder).listen(errors.write);
        child.stdout.drain<void>();
        final deadline = DateTime.now().add(const Duration(seconds: 45));
        while (!File('${root.path}/reader-ready').existsSync()) {
          if (DateTime.now().isAfter(deadline)) {
            fail('reader barrier timeout: $errors');
          }
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
        expect(child.kill(ProcessSignal.sigkill), true);
        expect(await child.exitCode, isNot(0));
        final direct = sqlite3.open(path);
        expect(
            direct.select('PRAGMA integrity_check').single.values.first, 'ok');
        expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
        expect(
            direct
                .select('SELECT current_id FROM accepted')
                .single['current_id'],
            publication.generationId);
        expect(
            direct
                .select('SELECT count(*) AS n FROM generation_roots')
                .single['n'],
            4);
        // Real write/COMMIT establishes that no response/read slot remains held.
        direct.execute('BEGIN IMMEDIATE');
        direct.execute('UPDATE accepted SET sequence=sequence WHERE id=1');
        direct.execute('COMMIT');
        direct.close();
        store = SegmentedClientStore.open(root, input.cache, publication: true);
        final recovered = await store.recoverAcceptedGeneration();
        expect(recovered.id, publication.generationId);
        expect(store.withAcceptedRead(recovered, (r) => r.rows('app_settings')),
            isNotEmpty);
        for (final e in before.entries) {
          expect(File(e.key).readAsBytesSync(), e.value);
        }
        final repo = Directory.current.parent.path;
        final verified = await Process.run('$repo/.venv/bin/python',
            ['$repo/mobile/test/support/e4_backend_oracle.py', root.path]);
        expect(verified.exitCode, 0, reason: verified.stderr as String);
        final recoveredLegacy = jsonDecode(verified.stdout as String) as Map;
        expect(recoveredLegacy['fingerprint'], baseline.serverStateFingerprint);
        expect(recoveredLegacy['lineage'],
            legacyStore.recoveryLineageFingerprint(baseline));
        expect(recoveredLegacy['journal_count'], 1);
      } finally {
        child?.kill(ProcessSignal.sigkill);
        store?.close();
        root.deleteSync(recursive: true);
      }
    });
  }
}
