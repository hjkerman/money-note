import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_e2_fixture.dart';

void main() {
  late Map<String, dynamic> initial, target;
  setUpAll(() async {
    final bridge = await BackendBridge.start();
    initial = bridge.fixture;
    await bridge.command({'command': 'mutate'});
    final temp =
        Directory.systemTemp.createTempSync('money-note-e3-crash-oracle-');
    final db = SegmentedClientStore.open(temp, GenerationFixture(initial).cache,
        publication: true);
    try {
      await IncrementalFetcher(db, FixtureTransport(GenerationFixture(initial)))
          .acquire();
      // Actual server observes and supplies the later immutable generation.
      final api = await bridge.command({
        'command': 'http',
        'method': 'POST',
        'path': '/api/sync/v1/observations',
        'headers': {
          'Authorization': 'Bearer ${bridge.token}',
          'Content-Type': 'application/json'
        },
        'body_base64': base64Encode(utf8.encode(jsonEncode({
          'protocol': 1,
          'request_id': syncUuid(),
          'base': null,
          'inline_bytes': 0
        })))
      });
      expect(api['status'], 201);
      target = await bridge.command({'command': 'oracle'});
    } finally {
      db.close();
      temp.deleteSync(recursive: true);
      await bridge.dispose();
    }
  });
  for (final rootPins in [false, true]) {
    for (final point in [
      'before_transaction',
      'after_generation_manifest',
      'after_generation_pins',
      'after_publication_begin',
      'after_accepted_pointer',
      'before_publication_commit',
      'after_publication_commit',
      'during_publication_readback'
    ]) {
      test(
          'real process kill at E3 $point roots=$rootPins; fresh accepted graph is coherent',
          () async {
        final root =
            Directory.systemTemp.createTempSync('money-note-e3-crash-');
        final first = GenerationFixture(initial),
            second = GenerationFixture(target);
        final db =
            SegmentedClientStore.open(root, first.cache, publication: true);
        final a =
            await IncrementalFetcher(db, FixtureTransport(first)).acquire();
        final version = db.publicationDataVersion;
        final proof = rootPins
            ? await db.verifyPublicationCandidate(
                a.manifest, db.acceptedGeneration(),
                verifiedDataVersion: version)
            : await verifyCompleteGeneration(
                a.manifest, (ref) => db.getVerifiedObject(ref)!);
        final prepared = db.prepareGeneration(
            syncUuid(), a.stagingId, proof, db.acceptedGeneration(),
            verifiedDataVersion: version);
        db.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
        final staged =
            await IncrementalFetcher(db, FixtureTransport(second)).acquire();
        final path = db.path;
        db.close();
        final fixtureFile = File('${root.path}/fixture.json')
          ..writeAsStringSync(jsonEncode(target));
        final ready = Completer<void>();
        final watch = root.watch().listen((e) {
          if (e.path.endsWith('/ready') && !ready.isCompleted) ready.complete();
        });
        final child = await Process.start('dart', [
          'run',
          'test/support/segmented_publication_crash_worker.dart',
          root.path,
          fixtureFile.path,
          staged.stagingId,
          point,
          if (rootPins) 'incremental'
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
          final reopened =
              SegmentedClientStore.open(root, first.cache, publication: true);
          try {
            final accepted = await reopened.recoverAcceptedGeneration();
            final committed = [
              'after_publication_commit',
              'during_publication_readback'
            ].contains(point);
            expect(accepted.sequence, committed ? 2 : 1);
            expect(accepted.manifest!.target.syncRoot,
                committed ? second.target.syncRoot : first.target.syncRoot);
            final direct = sqlite3.open(path);
            try {
              expect(
                  direct.select('PRAGMA integrity_check').single.values.first,
                  'ok');
              expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
              final pointer = direct.select('SELECT * FROM accepted').single;
              expect(pointer['sequence'], committed ? 2 : 1);
              final missing = direct.select(
                  'SELECT p.hash FROM generation_objects p LEFT JOIN objects o USING(hash) WHERE o.hash IS NULL');
              expect(missing, isEmpty);
              final closure = direct.select('''WITH RECURSIVE closure(hash) AS (
              SELECT hash FROM generation_objects WHERE generation_id=?
              UNION SELECT hash FROM generation_roots WHERE generation_id=?
              UNION SELECT e.child FROM edges e JOIN closure c ON e.parent=c.hash)
              SELECT hash FROM closure''',
                  [pointer['current_id'], pointer['current_id']]);
              expect(closure.map((r) => r['hash']).toSet(),
                  (committed ? second : first).objects.keys.toSet());
              if (rootPins) {
                expect(
                    direct.select(
                        'SELECT count(*) AS n FROM generation_roots WHERE generation_id=?',
                        [pointer['current_id']]).single['n'],
                    4);
              }
              direct.execute('BEGIN IMMEDIATE');
              direct.execute('ROLLBACK');
            } finally {
              direct.close();
            }
          } finally {
            reopened.close();
          }
        } finally {
          child.kill(ProcessSignal.sigkill);
          await watch.cancel();
          root.deleteSync(recursive: true);
        }
      }, timeout: const Timeout(Duration(minutes: 2)));
    }
  }
}
