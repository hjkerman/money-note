import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_e2_fixture.dart';

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
    'after_progress_insert'
  ]) {
    test('real process termination during E2 $point; restart/reacquire safely',
        () async {
      final root = Directory.systemTemp.createTempSync('money-note-e2-crash-');
      final fixture = GenerationFixture(data),
          file = File('${root.path}/fixture.json')
            ..writeAsStringSync(jsonEncode(data));
      final initialized =
              SegmentedClientStore.open(root, fixture.cache, acquisition: true),
          path = initialized.path;
      initialized.close();
      final ready = Completer<void>();
      final watch = root.watch().listen((e) {
        if (e.path.endsWith('/ready') && !ready.isCompleted) ready.complete();
      });
      final child = await Process.start('dart', [
        'run',
        'test/support/segmented_fetch_crash_worker.dart',
        root.path,
        file.path,
        point
      ]);
      final errors = child.stderr.transform(utf8.decoder).join(),
          drained = child.stdout.drain<void>();
      final exited = child.exitCode.then((code) async {
        if (!ready.isCompleted) {
          ready.completeError(StateError('child $code: ${await errors}'));
        }
        return code;
      });
      try {
        await ready.future.timeout(const Duration(seconds: 60));
        expect(child.kill(ProcessSignal.sigkill), isTrue);
        await exited;
        await drained;
        final db =
            SegmentedClientStore.open(root, fixture.cache, acquisition: true);
        try {
          final stage = db.listStagingIdentities().single,
              progress = db.acquisitionProgress(stage);
          expect(progress?.state,
              point == 'after_acquisition_insert' ? null : 'acquiring');
          final direct = sqlite3.open(path);
          expect(direct.select('PRAGMA integrity_check').single.values.first,
              'ok');
          expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
          expect(
              direct
                  .select('SELECT count(*) AS n FROM staging_objects')
                  .single['n'],
              0);
          direct.execute('BEGIN IMMEDIATE');
          direct.execute('ROLLBACK');
          direct.close();
          // Mock authority never persists outside child; replacement acquisition
          // re-establishes current server authorization, not a local timestamp.
          final transport = FixtureTransport(fixture);
          final result = await IncrementalFetcher(db, transport).acquire();
          expect(result.graph.objects.map((r) => r.hash).toSet(),
              fixture.objects.keys.toSet());
          expect(db.loadStaging(stage)!.validationState, 'staged');
        } finally {
          db.close();
        }
      } finally {
        child.kill(ProcessSignal.sigkill);
        await watch.cancel();
        root.deleteSync(recursive: true);
      }
    }, timeout: const Timeout(Duration(minutes: 2)));
  }
}
