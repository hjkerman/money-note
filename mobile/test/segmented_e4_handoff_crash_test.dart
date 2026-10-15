@Timeout(Duration(minutes: 10))
library;

import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:sqlite3/sqlite3.dart';
import 'support/e4_targeted_fixture.dart';
import 'support/offline_mode_fixtures.dart';
import 'support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Map<String, dynamic> wire;
  setUpAll(() async {
    wire = await e4WireOracle();
  });
  for (final point in [
    'before_frozen_prepare',
    'after_frozen_prepare',
    'after_source_prepare',
    'before_legacy_rename',
    'after_legacy_commit',
    'after_frozen_install',
    'before_pending_retire',
    'after_e4_installation',
    'native_before_source_rename',
    'native_after_segmented_install_pointer',
    'native_during_installation_readback',
    'native_before_pending_retire',
    'native_after_e4_installation'
  ]) {
    test(
        'T01/T02 actual SIGKILL $point preserves complete B/pins/pending and fresh recovery',
        () async {
      final root = Directory.systemTemp.createTempSync('mn-e4-durable-crash-');
      Process? process;
      SegmentedClientStore? recovered;
      try {
        File('${root.path}/e4-owned').writeAsStringSync('synthetic E4');
        final workspace = E4Workspace(root);
        final old = legacyBaseline(
            AuthoritativeBundle.decode(utf8.encode(jsonEncode(wire)))
                .toCoherentBundle(baselineFixture().user),
            DateTime.utc(2026, 10, 14));
        await workspace.replaceBaseline(old);
        final marker = await workspace.beginOnlineWrite(1);
        await workspace.savePendingOnlineWrite(marker.committed());
        final before = File('${workspace.root.path}/offline-mode/baseline.json')
                .readAsBytesSync(),
            markerBytes =
                File('${workspace.root.path}/offline-mode/online-write-1.json')
                    .readAsBytesSync();
        final errors = StringBuffer();
        process = await Process.start('/home/hjkerman/.flutter/bin/flutter', [
          'test',
          '--no-pub',
          '--machine',
          '--dart-define=E4_CRASH_ROOT=${root.path}',
          '--dart-define=E4_CRASH_POINT=$point',
          '../docs/benchmarks/t66e4-targeted/handoff_child_test.dart'
        ]);
        process.stderr.transform(utf8.decoder).listen(errors.write);
        process.stdout.transform(utf8.decoder).listen((s) {
          if (s.contains('"type":"error"')) errors.write(s);
        });
        int? exitedBeforeBarrier;
        process.exitCode.then((value) => exitedBeforeBarrier = value);
        final barrier = File('${root.path}/crash-ready.json'),
            deadline = DateTime.now().add(const Duration(seconds: 120));
        while (!barrier.existsSync()) {
          if (exitedBeforeBarrier != null) {
            fail('owned E4 child exited before barrier: $errors');
          }
          if (DateTime.now().isAfter(deadline)) {
            fail('owned E4 child barrier timeout: $errors');
          }
          await Future<void>.delayed(const Duration(milliseconds: 25));
        }
        final ready =
            jsonDecode(barrier.readAsStringSync()) as Map<String, dynamic>;
        expect(
            Process.killPid(ready['pid'] as int, ProcessSignal.sigkill), true);
        expect(await process.exitCode.timeout(const Duration(seconds: 45)),
            isNot(0));
        process = null;
        final path = ready['store_path'] as String, d = sqlite3.open(path);
        expect(d.select('PRAGMA integrity_check').single.values.first, 'ok');
        expect(d.select('PRAGMA foreign_key_check'), isEmpty);
        expect(d.select('SELECT current_id FROM accepted').single['current_id'],
            isNotNull);
        for (final f in d.select('SELECT * FROM frozen')) {
          final count = d.select(
              'WITH RECURSIVE c(hash) AS (SELECT hash FROM generation_roots WHERE generation_id=? UNION SELECT e.child FROM edges e JOIN c ON e.parent=c.hash) SELECT count(*) AS n FROM c',
              [f['generation_id']]).single['n'];
          expect(
              count,
              d.select('SELECT object_count FROM generations WHERE id=?',
                  [f['generation_id']]).single['object_count']);
        }
        d.execute('BEGIN IMMEDIATE');
        d.execute('COMMIT');
        final namespace = d
            .select('SELECT namespace FROM profile')
            .single['namespace'] as String;
        d.close();
        // Namespace is decoded from durable manifest using the actual API; no
        // authority or credential is restored from a persisted ticket.
        final raw = sqlite3.open(path);
        final manifest = jsonDecode(utf8.decode(raw
            .select(
                'SELECT manifest FROM generations WHERE id=(SELECT current_id FROM accepted)')
            .single['manifest'] as List<int>));
        raw.close();
        final cache = CacheNamespace.forTarget(
            syntheticOrigin, SyncTarget.parse(manifest['target']));
        expect(cache.key, namespace);
        recovered = SegmentedClientStore.open(root, cache, adapters: true);
        final fresh = E4Workspace(root);
        await fresh.recoverLegacyHandoff(recovered);
        await recovered.recoverAcceptedGeneration();
        final inspector =
            OfflineStore(directoryProvider: () => Future.value(fresh.root));
        final after = (await inspector.loadBaseline())!;
        final early = [
          'before_frozen_prepare',
          'after_frozen_prepare',
          'after_source_prepare',
          'before_legacy_rename'
        ].contains(point);
        if (point.startsWith('native_')) {
          expect(
              File('${fresh.root.path}/offline-mode/baseline.json')
                  .readAsBytesSync(),
              before);
          expect(recovered.frozenGenerations(), isEmpty);
          if ([
            'native_before_source_rename',
            'native_after_segmented_install_pointer'
          ].contains(point)) {
            expect(recovered.installedGeneration(), null);
          } else {
            expect(recovered.installedGeneration(), isNotNull);
          }
        } else if (early) {
          expect(
              File('${fresh.root.path}/offline-mode/baseline.json')
                  .readAsBytesSync(),
              before);
          expect(recovered.frozenGenerations(), isEmpty);
        } else {
          final f = recovered.frozenGenerations().single;
          expect(f.installed, true);
          expect(inspector.recoveryLineageFingerprint(after),
              f.binding['legacy_lineage']);
          expect(after.serverStateFingerprint, f.binding['legacy_fingerprint']);
          expect(after.serverStateFingerprint, isNot(f.target.syncRoot));
          await expectLater(fresh.loadBaseline(),
              throwsA(isA<OfflinePersistenceException>()));
        }
        final pending =
            File('${fresh.root.path}/offline-mode/online-write-1.json');
        if (point == 'after_e4_installation' ||
            point == 'native_after_e4_installation') {
          expect(pending.existsSync(), false);
        } else {
          expect(pending.readAsBytesSync(), markerBytes);
        }
        expect(await inspector.loadJournal(), isEmpty);
        // Separate Python process checks actual backend restore and fingerprint.
        final repo = Directory.current.parent.path;
        final check = await Process.run('$repo/.venv/bin/python', [
          '-c',
          'import json,sys; from app.services.snapshot import validate_reconciliation_snapshot,snapshot_state_fingerprint; b=json.load(open(sys.argv[1])); validate_reconciliation_snapshot(b["authoritative_snapshot"]); assert snapshot_state_fingerprint(b["authoritative_snapshot"])==b["server_state_fingerprint"]',
          '${fresh.root.path}/offline-mode/baseline.json'
        ], environment: {
          'PYTHONPATH': '$repo/backend'
        });
        expect(check.exitCode, 0, reason: check.stderr as String);
      } finally {
        process?.kill(ProcessSignal.sigkill);
        recovered?.close();
        root.deleteSync(recursive: true);
      }
    });
  }
}
