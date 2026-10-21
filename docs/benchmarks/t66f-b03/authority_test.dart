@Timeout(Duration(minutes: 4))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/segmented_logical_cost_http_test.dart';
import '../../../mobile/test/support/logical_cost_sqlite.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../t66f-phase-b/harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final mode in ['cancelled', 'stale-user']) {
    test(
      'B03 actual final authority $mode records rollback, never committed',
      () async {
        final backend = await CostBackend.start(0);
        final h = await RealHarness.create(RealBackend.remote(backend.initial));
        final collector = LogicalCost(), sql = SqlCosts();
        final cancel = SyncCancellation(), cache = h.store.cache;
        var reached = false;
        h.store.close();
        h.store = SegmentedClientStore.open(
          h.root,
          cache,
          adapters: true,
          diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), sql),
          fault: (point) {
            if (point != 'before_publication_commit') return;
            reached = true;
            if (mode == 'cancelled') {
              cancel.cancel();
            } else {
              h.state.user = null;
            }
          },
        );
        try {
          await h.workspace.replaceBaseline(baselineFixture());
          await h.workspace.beginOnlineWrite(1);
          final baseline = h.baseline.readAsBytesSync();
          final pending = h.pending.readAsBytesSync();
          await expectLater(
            collector.run(
              LogicalCostStage.e2,
              () => h.state.publishSegmentedForIsolatedUse(
                h.store,
                cancellation: cancel,
              ),
            ),
            throwsA(
              mode == 'cancelled'
                  ? isA<SegmentedException>().having(
                      (e) => e.code,
                      'code',
                      'ACQUISITION_CANCELLED',
                    )
                  : isA<MoneyNoteApiException>(),
            ),
          );
          expect(reached, isTrue);
          final db = sqlite3.open(h.store.path);
          try {
            expect(
              db.select('SELECT sequence FROM accepted').single['sequence'],
              0,
            );
            expect(db.select('SELECT * FROM generations'), isEmpty);
            expect(db.select('SELECT * FROM generation_objects'), isEmpty);
            expect(db.select('PRAGMA foreign_key_check'), isEmpty);
            expect(
              db.select('SELECT count(*) n FROM objects').single['n'],
              greaterThan(0),
            );
          } finally {
            db.close();
          }
          expect(
            sql.values['e3Commit/accepted/UPDATE/effective/rows'],
            BigInt.one,
          );
          expect(
            sql.values['e3Commit/accepted/UPDATE/textBytes/rolledBack'],
            greaterThan(BigInt.zero),
          );
          expect(
            sql.values['e3Commit/accepted/UPDATE/textBytes/committed'] ??
                BigInt.zero,
            BigInt.zero,
          );
          expect(
            collector.snapshot().keys.any((k) => k.startsWith('e3Verify/')),
            isTrue,
          );
          expect(h.baseline.readAsBytesSync(), baseline);
          expect(h.pending.readAsBytesSync(), pending);
          expect(LogicalCost.activeCollector, isNull);
          const output = String.fromEnvironment('B03_STALE_OUTPUT');
          if (output.isNotEmpty) {
            File('$output-$mode.json').writeAsStringSync(
              jsonEncode({
                'schema_version': 1,
                'fixture': 'synthetic real TLS final E3 authority',
                'mode': mode,
                'primitive': collector.snapshot(),
                'sqlite': sql.snapshot(),
                'accepted_sequence': 0,
                'pending_preserved': true,
              }),
            );
          }
        } finally {
          h.dispose();
          await backend.close();
        }
      },
    );
  }
}
