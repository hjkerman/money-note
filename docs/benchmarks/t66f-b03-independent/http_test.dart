@Timeout(Duration(minutes: 8))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/segmented_logical_cost_http_test.dart';
import '../../../mobile/test/support/logical_cost_sqlite.dart';
import '../t66f-phase-b/harness.dart';

Future<CostBackend> start() async {
  final root = Directory.current.parent.path;
  final p = await Process.start('$root/.venv/bin/python', [
    '$root/docs/benchmarks/t66f-b03-independent/server.py',
    '3',
  ]);
  final errors = StringBuffer();
  p.stderr.transform(utf8.decoder).listen(errors.write);
  final lines = StreamIterator(
    p.stdout.transform(utf8.decoder).transform(const LineSplitter()),
  );
  if (!await lines.moveNext().timeout(const Duration(minutes: 3))) {
    throw StateError('독립 TLS 시작 실패: $errors');
  }
  return CostBackend(p, lines, jsonDecode(lines.current));
}

void verifyNativeWitness(Map value) {
  final counters = (value['counters'] as Map).cast<String, String>();
  for (final e in counters.entries.where((e) => e.key.contains('/audit_'))) {
    final production = e.key.replaceFirst('/audit_', '/');
    expect(
      counters[production] ?? '0',
      e.value,
      reason: '실제 native primitive 직접 관측: $production',
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('independent small real TLS native oracle and durable E1/E3/E4', () async {
    final backend = await start();
    final harness = await RealHarness.create(
      RealBackend.remote(backend.initial),
    );
    final records = <String, dynamic>{};
    try {
      for (final enabled in [false, true]) {
        final h = enabled
            ? await RealHarness.create(RealBackend.remote(backend.initial))
            : harness;
        final c = LogicalCost(), s = SqlCosts();
        if (enabled) {
          final cache = h.store.cache;
          h.store.close();
          h.store = SegmentedClientStore.open(
            h.root,
            cache,
            adapters: true,
            diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), s),
          );
        }
        try {
          final coldTimer = Stopwatch()..start();
          final result = enabled
              ? await c.run(
                  LogicalCostStage.e2,
                  () => h.state.publishSegmentedForIsolatedUse(h.store),
                )
              : await h.state.publishSegmentedForIsolatedUse(h.store);
          final coldUs = coldTimer.elapsedMicroseconds;
          final native = sqlite3.open(h.store.path);
          late Map<String, dynamic> durable;
          try {
            final expected = (backend.initial['fixture']['objects'] as List)
                .cast<Map>();
            var bytes = 0, framed = 0;
            for (final object in expected) {
              final raw = base64Decode(object['data_base64']);
              bytes += raw.length;
              final kind =
                  (jsonDecode(utf8.decode(raw)) as Map)['kind'] as String;
              framed +=
                  raw.length +
                  ascii.encode('money-note.sync.v1/$kind').length +
                  1;
              expect(
                native.select('SELECT body FROM objects WHERE hash=?', [
                  object['ref']['hash'],
                ]).single['body'],
                raw,
              );
            }
            if (enabled) {
              expect(
                s.values['e2/objects/INSERT/blobBytes/committed'],
                BigInt.from(bytes),
              );
              expect(
                s.values['e2/objects/INSERT/effective/rows'],
                BigInt.from(expected.length),
              );
              // 모든 새 object는 admission hash/parse를 적어도 한 번 거친다.
              expect(
                BigInt.parse(c.snapshot()['e2/objectHash/hashInputBytes']!),
                greaterThanOrEqualTo(BigInt.from(framed)),
              );
              expect(
                BigInt.parse(c.snapshot()['e2/c1/submittedBytes']!),
                greaterThanOrEqualTo(BigInt.from(bytes)),
              );
              records['independent_bounds'] = {
                'canonical_bytes': bytes,
                'minimum_hash_preimage_bytes': framed,
                'unique_objects': expected.length,
              };
            }
            durable = {
              'root': h.store.acceptedGeneration().manifest!.target.syncRoot,
              'sequence': result.sequence,
              'objects': native
                  .select(
                    'SELECT hash,kind,hex(body) body FROM objects ORDER BY hash',
                  )
                  .map((r) => r.values.toList())
                  .toList(),
            };
          } finally {
            native.close();
          }
          final before = s.snapshot();
          final accepted = h.store.acceptedGeneration();
          final same = enabled
              ? await c.run(
                  LogicalCostStage.e2,
                  () => h.state.publishSegmentedForIsolatedUse(h.store),
                )
              : await h.state.publishSegmentedForIsolatedUse(h.store);
          expect(same.generationId, accepted.id);
          if (enabled) {
            expect(
              s.snapshot()['e2/objects/INSERT/blobBytes/committed'],
              before['e2/objects/INSERT/blobBytes/committed'],
            );
          }
          final allRows = <String, dynamic>{};
          c.run(LogicalCostStage.e4Read, () {
            h.store.withAcceptedRead(accepted, (r) {
              for (final name
                  in (backend.initial['fixture']['source'] as Map).keys) {
                allRows[name as String] = r.rows(name, limit: 256);
              }
            });
          });
          final source = backend.initial['fixture']['source'] as Map;
          for (final name in source.keys) {
            expect(
              allRows[name],
              unorderedEquals(source[name] as List),
              reason: 'backend 직접 SQL 원본과 E4의 전체 값 일치: $name',
            );
          }
          durable['financial_rows'] = allRows;
          final measurement = await backend.command({'command': 'cost'});
          verifyNativeWitness(measurement);
          records[enabled ? 'enabled' : 'disabled'] = {
            'cold_wall_us': coldUs,
            'durable': durable,
            'primitive': c.snapshot(),
            'sqlite': s.snapshot(),
            'backend': measurement,
          };
          final stats = await backend.command({
            'command': 'stats',
            'reset': true,
          });
          records[enabled ? 'enabled_http' : 'disabled_http'] = stats;
        } finally {
          if (enabled) h.dispose();
        }
      }
      expect(
        (records['enabled'] as Map)['durable'],
        (records['disabled'] as Map)['durable'],
      );
      File(
        '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-independent/evidence/independent-real-http.json',
      ).writeAsStringSync(jsonEncode(records));
    } finally {
      harness.dispose();
      await backend.close();
    }
  });

  test('independent overlapping TLS distinguishable authentication workloads', () async {
    final backend = await start();
    final clients = <HttpClient>[];
    try {
      Future<int> request(String token) async {
        final io = HttpOverrides.runWithHttpOverrides(
          () => HttpClient(),
          RealHttpOverrides(),
        );
        clients.add(io);
        io.badCertificateCallback = (_, h, p) =>
            h == '127.0.0.1' && p == Uri.parse(backend.initial['origin']).port;
        final req = await io.postUrl(
          Uri.parse('${backend.initial['origin']}/api/sync/v1/observations'),
        );
        req.headers.set('Authorization', 'Bearer $token');
        req.headers.set('Content-Type', 'application/json');
        req.headers.set('X-B03-Barrier', 'pair');
        req.write(
          jsonEncode({
            'protocol': 1,
            'request_id': '12345678-1234-4234-8234-123456789abc',
            'base': null,
            'inline_bytes': 0,
          }),
        );
        final response = await req.close();
        await response.drain<void>();
        return response.statusCode;
      }

      final statuses = await Future.wait([
        request(backend.initial['token']),
        request('independent-invalid-token'),
      ]);
      expect(statuses, [201, 401]);
      final measured = await backend.command({
        'command': 'cost',
        'after_requests': 2,
      });
      verifyNativeWitness(measured);
      final samples = (measured['request_samples'] as List).cast<Map>();
      expect(samples.length, 2);
      for (final sample in samples) {
        verifyNativeWitness(sample);
        final values = sample['counters'] as Map;
        expect(
          values['observation/authentication_sha256/hash_input_bytes'],
          '${sample['status'] == 401 ? utf8.encode('independent-invalid-token').length : utf8.encode(backend.initial['token']).length}',
        );
        if (sample['status'] == 401) {
          // body admission은 credential 검사보다 먼저 실행된다.
          expect(values['observation/json/calls'], '1');
          final raw = utf8.encode(
            jsonEncode({
              'protocol': 1,
              'request_id': '12345678-1234-4234-8234-123456789abc',
              'base': null,
              'inline_bytes': 0,
            }),
          );
          expect(values['observation/json/submitted_bytes'], '${raw.length}');
          expect(values['observation/json/completed_bytes'], '${raw.length}');
        }
      }
      for (final io in clients) {
        io.close(force: true);
      }
      final tail = await backend.command({'command': 'cost'});
      expect(tail['counters'], measured['counters']);
      File(
        '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-independent/evidence/independent-tls-concurrency.json',
      ).writeAsStringSync(jsonEncode(measured));
    } finally {
      for (final io in clients) {
        io.close(force: true);
      }
      await backend.close();
    }
  });
}
