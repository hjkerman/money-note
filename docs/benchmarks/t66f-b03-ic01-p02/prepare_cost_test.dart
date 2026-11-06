import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';
import 'original_sqlite.dart' as before;

void main() {
  test('P01 strict existing prepared API isolates repeated trigger compilation', () {
    const source = String.fromEnvironment(
      'P02_SOURCE',
      defaultValue: '/tmp/mn-b02-independent-100000-z6ux9y53',
    );
    final path = Directory('$source/client/segmented-store-v1')
        .listSync()
        .whereType<File>()
        .single
        .path;
    final original = sqlite3.open(path, mode: OpenMode.readOnly);
    late List<Uint8List> payloads;
    try {
      payloads = [
        for (final r in original.select(
          "SELECT body FROM objects WHERE kind='index-leaf' ORDER BY hash LIMIT 2048",
        ))
          r['body'] as Uint8List,
      ];
    } finally {
      original.close();
    }
    final records = <Map<String, Object?>>[];
    final expected = payloads.fold<int>(0, (n, b) => n + b.length);
    for (var repeat = 0; repeat < 6; repeat++) {
      Map<String, String>? oracle;
      for (final mode
          in repeat.isEven
              ? ['original', 'explicit', 'cache']
              : ['cache', 'explicit', 'original']) {
        final prepared = mode == 'explicit';
        final native = sqlite3.openInMemory(), c = LogicalCost();
        final dynamic s = mode == 'cache' ? SqlCosts() : before.SqlCosts();
        final dynamic d = mode == 'cache'
            ? CostDatabase(native, s)
            : before.CostDatabase(native, s);
        try {
          d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB NOT NULL)');
          PreparedStatement? statement;
          final timer = Stopwatch()..start();
          c.run(LogicalCostStage.e1, () {
            d.execute('BEGIN');
            if (prepared)
              statement = d.prepare(
                'INSERT INTO payload VALUES(?,?)',
                persistent: true,
                checkNoTail: true,
              );
            for (var i = 0; i < payloads.length; i++) {
              final args = <Object?>['$i', payloads[i]];
              if (prepared) {
                statement!.execute(args);
              } else {
                d.execute('INSERT INTO payload VALUES(?,?)', args);
              }
            }
            statement?.close();
            d.execute('COMMIT');
          });
          final elapsed = timer.elapsedMicroseconds;
          final actual = native
              .select('SELECT count(*) n,sum(length(b)) b FROM payload')
              .single;
          expect(actual['n'], payloads.length);
          expect(actual['b'], expected);
          expect(
            s.values['e1/payload/INSERT/blobBytes/committed'],
            BigInt.from(expected),
          );
          final snapshot = s.snapshot();
          if (oracle == null) {
            oracle = snapshot;
          } else {
            expect(
              snapshot,
              oracle,
              reason: 'identical attempted/effective/committed and all existing diagnostic counts',
            );
          }
          if (repeat > 0)
            records.add({
              'prepared': prepared,
              'mode': mode,
              'cache': mode == 'cache'
                  ? Map<String, int>.of(d.statementReuse)
                  : null,
              'repeat': repeat,
              'wall_us': elapsed,
              'sql': snapshot,
            });
        } finally {
          d.close();
          c.close();
        }
      }
    }
    File(
      '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-ic01-p02/evidence/${const bool.fromEnvironment("P02_FINAL") ? "preparation-final-data" : "preparation-results"}.json',
    ).writeAsStringSync(
      jsonEncode({
        'objects': payloads.length,
        'bytes': expected,
        'records': records,
        'scope': 'isolated actual immutable input SQL, supported original CostDatabase.prepare vs execute; not a changed production E1 path or full graph',
        'product_changes': false,
      }),
    );
  });
}
