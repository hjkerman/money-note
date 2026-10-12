import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_fixture.dart';

void main() {
  for (final point in [
    'before_object_insert',
    'after_object_insert',
    'after_edges_insert',
    'before_commit',
    'after_commit',
    'after_staging_insert',
    'after_staging_commit'
  ]) {
    test('actual process death and fresh recovery $point', () async {
      final root = Directory.systemTemp.createTempSync('money-note-e1-crash-');
      final golden = ServerGolden();
      final initial = SegmentedClientStore.open(root, golden.cache);
      final path = initial.path;
      initial.putVerifiedObject(
          golden.ref('index-empty'), golden.bytes('index-empty'));
      initial.close();
      final ready = Completer<void>();
      final subscription = root.watch().listen((event) {
        if (event.path.endsWith('/ready') && !ready.isCompleted) {
          ready.complete();
        }
      });
      Process? child;
      try {
        child = await Process.start('dart', [
          'run',
          'test/support/segmented_crash_worker.dart',
          root.path,
          File('test/fixtures/segmented_server_golden.json').absolute.path,
          point
        ]);
        final errors =
            child.stderr.transform(const SystemEncoding().decoder).join();
        final stdoutDrained = child.stdout.drain<void>();
        final exited = child.exitCode.then((code) async {
          if (!ready.isCompleted) {
            ready.completeError(
                StateError('child exited $code: ${await errors}'));
          }
          return code;
        });
        await ready.future.timeout(const Duration(seconds: 60));
        expect(child.kill(ProcessSignal.sigkill), isTrue);
        await exited;
        await stdoutDrained;
        final recovered = SegmentedClientStore.open(root, golden.cache);
        try {
          expect(recovered.getVerifiedObject(golden.ref('index-empty')),
              isNotNull);
          expect(recovered.getVerifiedObject(golden.ref('raw-root')) != null,
              point == 'after_commit');
          if (point == 'after_staging_commit') {
            final staged = recovered.loadStaging(stageId)!;
            expect(staged.manifest.bytes, golden.manifest.bytes);
            expect(staged.objectCount, 0);
            expect(staged.validationState, 'staged');
          } else {
            expect(recovered.loadStaging(stageId), isNull);
          }
          expect(recovered.inspectStoreHealth().healthy, isTrue);
          final direct = sqlite3.open(path);
          try {
            expect(direct.select('PRAGMA integrity_check').single.values.first,
                'ok');
            expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
            expect(
                direct.select('SELECT count(*) AS n FROM staging').single['n'],
                point == 'after_staging_commit' ? 1 : 0);
            expect(
                direct
                    .select('SELECT count(*) AS n FROM staging_roots')
                    .single['n'],
                point == 'after_staging_commit' ? 4 : 0);
            expect(
                direct.select('SELECT count(*) AS n FROM objects').single['n'],
                point == 'after_commit' ? 2 : 1);
            direct.execute('BEGIN IMMEDIATE');
            direct.execute('ROLLBACK');
          } finally {
            direct.close();
          }
        } finally {
          recovered.close();
        }
      } finally {
        child?.kill(ProcessSignal.sigkill);
        await subscription.cancel();
        root.deleteSync(recursive: true);
      }
    }, timeout: const Timeout(Duration(minutes: 2)));
  }
}
