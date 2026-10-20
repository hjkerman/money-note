@Timeout(Duration(minutes: 3))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../docs/benchmarks/t66f-b02-implementation/verification_profile.dart';
import 'support/offline_mode_fixtures.dart';
import 'support/segmented_e2_fixture.dart';
import 'support/segmented_large_transport.dart';

void main() {
  late Map<String, dynamic> data;
  setUpAll(() async {
    final bridge = await BackendBridge.start();
    data = bridge.fixture;
    await bridge.dispose();
  });
  for (final point in [
    'after_acquisition_insert',
    'after_acquisition_commit',
    'after_progress_insert',
    'batch_middle'
  ]) {
    test(
        'B02 selected profile real SIGKILL at $point preserves prior legacy/pending',
        () async {
      final root = Directory.systemTemp.createTempSync('mn-b02-kill-');
      final fixture = GenerationFixture(data);
      final file = File('${root.path}/fixture.json')
        ..writeAsStringSync(jsonEncode(data));
      final legacy = OfflineStore(directoryProvider: () async => root);
      await legacy.replaceBaseline(baselineFixture());
      await legacy.beginOnlineWrite(1);
      final before = {
        for (final f in Directory('${root.path}/offline-mode')
            .listSync()
            .whereType<File>())
          f.path: f.readAsBytesSync()
      };
      final ready = Completer<void>();
      final watch = root.watch().listen((event) {
        if (event.path.endsWith('/ready') && !ready.isCompleted) {
          ready.complete();
        }
      });
      final child = await Process.start('dart', [
        '--packages=.dart_tool/package_config.json',
        '../docs/benchmarks/t66f-b02-implementation/large_crash_worker.dart',
        root.path,
        file.path,
        point,
      ]);
      final errors = child.stderr.transform(utf8.decoder).join();
      final drained = child.stdout.drain<void>();
      final exited = child.exitCode.then((code) async {
        if (!ready.isCompleted) {
          ready.completeError(StateError('child $code: ${await errors}'));
        }
        return code;
      });
      try {
        await ready.future.timeout(const Duration(seconds: 60));
        expect(child.kill(ProcessSignal.sigkill), isTrue);
        expect(await exited, isNot(0));
        await drained;
        final store = SegmentedClientStore.open(root, fixture.cache,
            acquisition: true, limits: largeVerificationStoreLimits);
        try {
          final db = sqlite3.open(store.path);
          try {
            expect(
                db.select('PRAGMA integrity_check').single.values.single, 'ok');
            expect(db.select('PRAGMA foreign_key_check'), isEmpty);
            expect(
                db
                    .select('SELECT count(*) AS n FROM staging_objects')
                    .single['n'],
                point == 'batch_middle' ? 1 : 0);
            db.execute('BEGIN IMMEDIATE');
            db.execute('ROLLBACK');
          } finally {
            db.close();
          }
          final stage = store.listStagingIdentities().single;
          expect(store.acquisitionProgress(stage)?.state,
              point == 'after_acquisition_insert' ? null : 'acquiring');
          final complete = await IncrementalFetcher(
                  store, BatchFixtureTransport(fixture),
                  limits: largeVerificationFetchLimits)
              .acquire();
          expect(complete.graph.objects.map((o) => o.hash).toSet(),
              fixture.objects.keys.toSet());
          expect(store.inspectStoreHealth().healthy, isTrue);
        } finally {
          store.close();
        }
        for (final e in before.entries) {
          expect(File(e.key).readAsBytesSync(), e.value);
        }
        expect(await legacy.loadPendingOnlineWrite(1), isNotNull);
      } finally {
        child.kill(ProcessSignal.sigkill);
        await watch.cancel();
        root.deleteSync(recursive: true);
      }
    });
  }
}
