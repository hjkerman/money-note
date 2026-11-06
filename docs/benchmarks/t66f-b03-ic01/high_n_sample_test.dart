@Timeout(Duration(minutes: 8))
library;

import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';
import '../t66f-b02-implementation/verification_profile.dart';

void main() {
  test('IC01 bounded actual historical 100k object sample E1 overhead', () {
    const source = '/tmp/mn-b02-independent-100000-z6ux9y53';
    final fixture = jsonDecode(
      File('$source/server/backend-fixture.json').readAsStringSync(),
    ) as Map;
    final manifest = ObservationManifest.fromBytes(
      utf8.encode(jsonEncode(fixture['manifest'])),
    );
    final dbPath = Directory('$source/client/segmented-store-v1')
        .listSync()
        .whereType<File>()
        .single
        .path;
    final original = sqlite3.open(dbPath, mode: OpenMode.readOnly);
    final entries = <({ObjectRef ref, List<int>? bytes})>[];
    final distribution = <String, int>{};
    try {
      for (final kind in [
        'index-leaf',
        'index-node',
        'snapshot-leaf',
        'snapshot-node',
        'raw-root',
        'index-root',
        'hot',
        'control',
      ]) {
        final limit = kind.startsWith('index-') && kind != 'index-root'
            ? 1024
            : (kind == 'snapshot-leaf' ? 8 : 1);
        final rows = original.select(
          'SELECT hash,body FROM objects WHERE kind=? ORDER BY hash LIMIT ?',
          [kind, limit],
        );
        distribution[kind] = rows.length;
        for (final row in rows) {
          final bytes = Uint8List.fromList(row['body'] as Uint8List);
          entries.add((
            ref: ObjectRef.parse({
              'hash': row['hash'],
              'bytes': '${bytes.length}',
            }),
            bytes: bytes,
          ));
        }
      }
    } finally {
      original.close();
    }
    final payload = entries.fold<int>(0, (n, e) => n + e.bytes!.length);
    expect(payload, lessThan(16 * 1024 * 1024));
    final samples = <Map<String, dynamic>>[];
    for (var repeat = 0; repeat < 6; repeat++) {
      for (final enabled in repeat.isEven ? [false, true] : [true, false]) {
        final root = Directory.systemTemp.createTempSync('mn-ic01-sample-');
        final c = LogicalCost(), costs = SqlCosts();
        final cache = CacheNamespace.forTarget(
          'https://synthetic-sample.invalid',
          manifest.target,
        );
        final store = SegmentedClientStore.open(
          root,
          cache,
          acquisition: true,
          limits: largeVerificationStoreLimits,
          diagnosticDatabaseFactory: enabled
              ? (p) => CostDatabase(sqlite3.open(p), costs)
              : null,
        );
        try {
          store.createStaging(
            '12345678-1234-4234-8234-123456789abc',
            manifest,
            DateTime.utc(2026, 10, 5),
          );
          final timer = Stopwatch()..start();
          void write() {
            var start = 0;
            while (start < entries.length) {
              var end = start, bytes = 0;
              while (end < entries.length &&
                  end - start < 64 &&
                  bytes + entries[end].bytes!.length <= 1048576) {
                bytes += entries[end].bytes!.length;
                end++;
              }
              expect(end, greaterThan(start));
              store.putVerifiedStagedBatch(
                '12345678-1234-4234-8234-123456789abc',
                entries.sublist(start, end),
              );
              start = end;
            }
          }

          if (enabled) {
            c.run(LogicalCostStage.e2, write);
          } else {
            write();
          }
          final elapsed = timer.elapsedMicroseconds;
          final inspection = sqlite3.open(store.path, mode: OpenMode.readOnly);
          try {
            final row = inspection
                .select('SELECT count(*) n,sum(length(body)) b FROM objects')
                .single;
            expect(row['n'], entries.length);
            expect(row['b'], payload);
            // Acquisition-only E1 does not expose the E3 publication API.
            // Inspect actual SQLite state rather than enabling that profile.
            expect(
              inspection
                  .select(
                    "SELECT count(*) n FROM sqlite_master WHERE name IN ('accepted','generations')",
                  )
                  .single['n'],
              0,
            );
          } finally {
            inspection.close();
          }
          if (enabled) {
            expect(
              costs.values['e2/objects/INSERT/blobBytes/committed'],
              BigInt.from(payload),
            );
          }
          if (repeat > 0) {
            samples.add({
              'enabled': enabled,
              'repeat': repeat,
              'microseconds': elapsed,
              'rss_bytes': ProcessInfo.currentRss,
              'primitive': c.snapshot(),
              'sql': costs.snapshot(),
              'store_work': store.work.snapshot(),
            });
          }
        } finally {
          store.close();
          root.deleteSync(recursive: true);
        }
      }
    }
    File(
      '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-ic01/evidence/high-n-sample-result.json',
    ).writeAsStringSync(
      jsonEncode({
        'source':
            'historical synthetic 100k after valid delta phases; read-only',
        'objects': entries.length,
        'payload_bytes': payload,
        'distribution': distribution,
        'samples': samples,
        'max_rss_bytes': ProcessInfo.maxRss,
        'limits': 'E1 actual bounded staging only. No HTTP/observation/E3/E4 and NOT an instrumented 100k cold completion.',
      }),
    );
  });
}
