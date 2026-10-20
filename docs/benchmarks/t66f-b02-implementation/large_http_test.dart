@Timeout(Duration(hours: 2))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/offline_mode_fixtures.dart';
import 'verification_profile.dart';

class _RealLoopback extends HttpOverrides {}

void save(File file, Object? value) => file.writeAsStringSync(
  '${const JsonEncoder.withIndent('  ').convert(value)}\n',
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test(
    'B02 real cold D→E, original AppState ticket and closed R1 gate',
    () async {
      const n = int.fromEnvironment('B02_N', defaultValue: 50000);
      final out = Directory(const String.fromEnvironment('B02_OUT'));
      expect(out.existsSync(), isTrue);
      FlutterSecureStorage.setMockInitialValues({});
      final repo = Directory.current.parent.path;
      final process = await Process.start('$repo/.venv/bin/python', [
        '$repo/docs/benchmarks/t66f-b02-implementation/server.py',
        '$n',
        '${out.path}/server',
      ]);
      final errorLog = File('${out.path}/server.stderr').openWrite();
      process.stderr.listen(errorLog.add);
      final lines = StreamIterator(
        process.stdout.transform(utf8.decoder).transform(const LineSplitter()),
      );
      if (!await lines.moveNext().timeout(const Duration(minutes: 30))) {
        throw StateError('synthetic backend startup failed');
      }
      final init = jsonDecode(lines.current) as Map<String, dynamic>;
      final origin = init['origin'] as String;
      final fixture = init['fixture'] as Map<String, dynamic>;
      final target = SyncTarget.parse(fixture['manifest']['target']);
      final root = Directory('${out.path}/client')..createSync();
      final faults = <String, int>{};
      var store = SegmentedClientStore.open(
        root,
        CacheNamespace.forTarget(origin, target),
        adapters: true,
        limits: largeVerificationStoreLimits,
        fault: (p) => faults.update(p, (n) => n + 1, ifAbsent: () => 1),
      );
      final legacy = OfflineStore(directoryProvider: () async => root);
      await legacy.replaceBaseline(baselineFixture());
      await legacy.beginOnlineWrite(1);
      final protected = <String, String>{
        for (final f in Directory(
          '${root.path}/offline-mode',
        ).listSync().whereType<File>())
          f.path: localChecksum(f.readAsBytesSync()),
      };
      final native = HttpOverrides.runWithHttpOverrides(
        () => HttpClient(),
        _RealLoopback(),
      )..maxConnectionsPerHost = 1;
      native.badCertificateCallback = (_, host, port) =>
          host == '127.0.0.1' && port == Uri.parse(origin).port;
      final http = IOClient(native);
      final api = MoneyNoteApiClient(client: http, baseUrl: origin);
      await api.saveSession(init['token'] as String);
      final state = AppState(api, offlineStore: legacy)
        ..user = baselineFixture().user;
      final watch = Stopwatch()..start();
      var peakRss = ProcessInfo.currentRss;
      final sampler = Timer.periodic(const Duration(seconds: 1), (_) {
        if (ProcessInfo.currentRss > peakRss) peakRss = ProcessInfo.currentRss;
      });
      final result = <String, dynamic>{
        'n': n,
        'fixture': fixture['graph'],
        'store_path': store.path,
        'origin': origin,
        'real_clock': true,
        'lease_seconds': 900,
        'selection': 'explicit isolated publication parameter',
        'status': 'RUNNING',
        'profile_object_limit': store.limits.objectCount,
        'profile_metadata_limit': store.limits.metadataBytes,
        'accepted_before': store.acceptedGeneration().id,
        'protected_legacy_before': protected,
      };
      save(File('${out.path}/result.json'), result);
      Object? failed;
      var phase = 'cold';
      Future<Map<String, dynamic>> command(Map<String, dynamic> value) async {
        process.stdin.writeln(jsonEncode(value));
        if (!await lines.moveNext()) throw StateError('synthetic server ended');
        return jsonDecode(lines.current) as Map<String, dynamic>;
      }

      try {
        final publication = await state.publishSegmentedForIsolatedUse(
          store,
          verificationLimits: largeVerificationFetchLimits,
        );
        final accepted = store.acceptedGeneration();
        expect(accepted.id, publication.generationId);
        expect(accepted.manifest!.target.syncRoot, target.syncRoot);
        final page = store.withAcceptedRead(
          accepted,
          (view) => view.rows('ledger_entries', limit: 16),
        );
        expect(page.length, 16);
        result['accepted_after'] = accepted.id;
        result['read_row_ids'] = page.map((r) => r['id']).toList();
        result['status'] = 'PASS_COLD';
        result['cold_elapsed_us'] = watch.elapsedMicroseconds;
        result['cold_publication_transaction_us'] =
            publication.transactionMicroseconds;
        save(File('${out.path}/result.json'), result);
        if (const bool.fromEnvironment('B02_COMPLETE_PLAN')) {
          final phases = <Map<String, dynamic>>[];
          result['phases'] = phases;
          Future<void> publish(
            String name, {
            Map<String, dynamic>? expected,
          }) async {
            phase = name;
            final old = store.acceptedGeneration(),
                work = store.work.snapshot();
            final before = (await command({'command': 'stats'}))['wire'] as Map;
            final timing = Stopwatch()..start();
            final p = await state.publishSegmentedForIsolatedUse(
              store,
              verificationLimits: largeVerificationFetchLimits,
            );
            final counters = store.work.since(work);
            final now = store.acceptedGeneration();
            final after = (await command({'command': 'stats'}))['wire'] as Map;
            final transferred =
                (after['chunks'] as int) - (before['chunks'] as int);
            if (expected == null) {
              expect(p.idempotent, isTrue);
              expect(now.id, old.id);
              expect(transferred, 0);
            } else {
              expect(
                now.manifest!.target.syncRoot,
                expected['target']['sync_root'],
              );
              expect(transferred, expected['new_objects']);
              final actual = store
                  .withAcceptedRead(
                    now,
                    (view) => view.rows(
                      'ledger_entries',
                      after: TreeKey.parse(['i', '1001'], 'ledger_entries'),
                      limit: 1,
                    ),
                  )
                  .single;
              expect(encodeC1(actual), encodeC1(expected['expected_row']));
            }
            if (name != 'restart_delta') {
              expect(counters['full_recoveries'] ?? 0, 0);
              expect(counters['full_verifications'] ?? 0, 0);
            }
            phases.add({
              'phase': name,
              'elapsed_us': timing.elapsedMicroseconds,
              'publication_transaction_us': p.transactionMicroseconds,
              'transferred_objects': transferred,
              'store_work': counters,
              'http_delta': {
                for (final key in after.keys)
                  key: (after[key] as num) - ((before[key] as num?) ?? 0),
              },
              'expected_new_objects': expected?['new_objects'],
              'expected_reused_objects': expected?['reused_objects'],
              'generation': now.id,
              'sequence': now.sequence,
            });
            result['accepted_after'] = now.id;
            save(File('${out.path}/result.json'), result);
          }

          await publish('identical');
          final one = await command({'command': 'mutate', 'amount': 123456});
          await publish('one_row_delta', expected: one);
          final multiple = await command({
            'command': 'mutate',
            'amount': 123457,
            'multiple': true,
          });
          await publish('multiple_localized', expected: multiple);
          store.close();
          final reopened = await Process.run(
            '/home/hjkerman/.flutter/bin/dart',
            [
              '--packages=$repo/mobile/.dart_tool/package_config.json',
              '$repo/docs/benchmarks/t66f-b02-implementation/reopen.dart',
              out.path,
            ],
          );
          expect(reopened.exitCode, 0, reason: '${reopened.stderr}');
          result['fresh_process_exit'] = reopened.exitCode;
          store = SegmentedClientStore.open(
            root,
            CacheNamespace.forTarget(origin, target),
            adapters: true,
            limits: largeVerificationStoreLimits,
          );
          final restarted = await command({
            'command': 'mutate',
            'amount': 123458,
          });
          await publish('restart_delta', expected: restarted);
          result['status'] = 'PASS_COLD_IDENTICAL_DELTAS_RESTART';
        }
      } catch (error) {
        failed = error;
        result['status'] = 'FAIL_${phase.toUpperCase()}';
        result['error'] = error.toString();
        result['accepted_after'] = store.acceptedGeneration().id;
        if (phase == 'cold')
          expect(result['accepted_after'], isNull);
        else
          expect(result['accepted_after'], isNotNull);
      } finally {
        sampler.cancel();
        result['elapsed_us'] = watch.elapsedMicroseconds;
        result['sampled_client_rss_peak_bytes'] = peakRss;
        result['client_process_rss_peak_bytes'] = ProcessInfo.maxRss;
        result['store_work'] = store.work.snapshot();
        result['fault_boundary_counts'] = faults;
        result['protected_legacy_after'] = {
          for (final p in protected.keys)
            p: localChecksum(File(p).readAsBytesSync()),
        };
        expect(result['protected_legacy_after'], protected);
        final direct = sqlite3.open(store.path);
        try {
          result['usage'] = Map<String, dynamic>.from(
            direct.select('SELECT * FROM usage').single,
          );
          result['acquisition'] = direct
              .select('SELECT state,error_code FROM acquisition')
              .map((r) => Map<String, dynamic>.from(r))
              .toList();
          result['accepted_sql'] = direct
              .select('SELECT * FROM accepted')
              .map((r) => Map<String, dynamic>.from(r))
              .toList();
          result['generation_count'] = direct
              .select('SELECT count(*) AS n FROM generations')
              .single['n'];
          result['pin_rows'] = direct
              .select('SELECT count(*) AS n FROM generation_roots')
              .single['n'];
          result['foreign_key_errors'] = direct
              .select('PRAGMA foreign_key_check')
              .length;
          expect(result['foreign_key_errors'], 0);
        } finally {
          direct.close();
        }
        result['e1_database_bytes'] = File(store.path).lengthSync();
        result['r1_activation'] = 'CLOSED';
        save(File('${out.path}/result.json'), result);
        store.close();
        state.dispose();
        http.close();
        process.stdin.writeln(jsonEncode({'command': 'stats'}));
        if (await lines.moveNext()) {
          save(
            File('${out.path}/server-final-stats.json'),
            jsonDecode(lines.current),
          );
        }
        process.stdin.writeln(jsonEncode({'command': 'exit'}));
        await lines.moveNext();
        await process.stdin.close();
        expect(await process.exitCode.timeout(const Duration(seconds: 30)), 0);
        await lines.cancel();
        await errorLog.close();
      }
      if (failed != null) throw failed;
    },
  );
}
