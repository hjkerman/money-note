@Timeout(Duration(minutes: 20))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

// Fixture characterization only; never a replacement for an original assertion.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('original global-first-leaf selector can choose outside Frozen-B closure', () async {
    final bridge = await BackendBridge.start(history: 5);
    final h = await E4Harness.create(bridge, await e4WireOracle());
    try {
      final frozen = (await h.install()).frozen;
      final b = h.baselineFile.readAsBytesSync();
      final source = File('${h.workspace.root.path}/e4-source.json');
      final sourceBytes = source.readAsBytesSync();
      Map<String, dynamic>? selected;
      var attempts = 0;
      for (; attempts < 256; attempts++) {
        await bridge.command({'command': 'mutate'});
        await h.state.publishSegmentedForIsolatedUse(h.store);
        final db = sqlite3.open(h.store.path);
        try {
          // EXACT original selector, not a guessed or hand-picked foreign hash.
          final row = db
              .select(
                "SELECT hash,body FROM objects WHERE "
                "kind='snapshot-leaf' ORDER BY hash LIMIT 1",
              )
              .single;
          final member = db.select(
            'WITH RECURSIVE closure(hash) AS '
            '(SELECT hash FROM generation_roots WHERE generation_id=? UNION '
            'SELECT e.child FROM edges e JOIN closure c ON e.parent=c.hash) '
            'SELECT hash FROM closure WHERE hash=?',
            [frozen.generationId, row['hash']],
          );
          if (member.isEmpty) {
            selected = Map<String, dynamic>.from(row);
            final immutable =
                db
                        .select(
                          "SELECT sql FROM sqlite_master "
                          "WHERE name='immutable_body'",
                        )
                        .single['sql']
                    as String;
            final original = List<int>.from(row['body'] as List<int>);
            final offset = utf8.decode(original).indexOf('"canon":1') + 8;
            expect(original[offset], 49);
            final corrupt = List<int>.of(original)..[offset] = 50;
            db.execute('DROP TRIGGER immutable_body');
            db.execute('UPDATE objects SET body=? WHERE hash=?', [
              corrupt,
              row['hash'],
            ]);
            db.execute(immutable); // Same canonical/hash-invalid injection.
            break;
          }
        } finally {
          db.close();
        }
      }
      expect(selected, isNotNull, reason: 'bounded independent fixture search');
      h.reopen(); // No cached proof can hide the deliberate foreign corruption.
      final fresh = await h.workspace.readFrozenBaseline(h.store, frozen.id, 1);
      expect(
        h.workspace.recoveryLineageFingerprint(fresh),
        frozen.binding['legacy_lineage'],
      );
      expect(source.readAsBytesSync(), sourceBytes);
      expect(h.baselineFile.readAsBytesSync(), b);
      const out = String.fromEnvironment('RA01_SELECTOR_OUTPUT');
      File(out).writeAsStringSync(
        jsonEncode({
          'selected_hash': selected!['hash'],
          'attempts': attempts + 1,
          'frozen_generation': frozen.generationId,
          'reachable_from_frozen': false,
          'fresh_frozen_read': true,
          'source_preserved': true,
          'baseline_preserved': true,
          'source_sha256': localChecksum(sourceBytes),
          'baseline_sha256': localChecksum(b),
          'scope':
              'fixture attribution, not a new publication correctness case',
        }),
      );
    } finally {
      h.dispose();
      await bridge.dispose();
    }
  });
}
