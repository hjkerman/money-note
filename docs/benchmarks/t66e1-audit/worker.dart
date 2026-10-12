// 독립 감사 전용. 호출자가 새로 만든 disposable 디렉터리만 사용한다.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

void main(List<String> args) {
  final job =
      jsonDecode(File(args[0]).readAsStringSync()) as Map<String, dynamic>;
  SegmentedClientStore? store;
  try {
    if (job['action'] == 'canonical') {
      final results = <Map<String, dynamic>>[];
      for (final item in job['vectors'] as List) {
        try {
          final raw = base64Decode(item['raw'] as String);
          final body = decodeC1(
            raw,
            requireCanonical: item['canonical'] as bool? ?? true,
          );
          final exact = encodeC1(body);
          results.add({
            'ok': true,
            'bytes': base64Encode(exact),
            'hash': objectHash('view', exact),
          });
        } catch (error) {
          results.add({'ok': false, 'error': '$error'});
        }
      }
      stdout.writeln(jsonEncode({'ok': true, 'results': results}));
      return;
    }
    final fixture = jsonDecode(
      File(job['fixture'] as String).readAsStringSync(),
    ) as Map<String, dynamic>;
    final manifest = ObservationManifest.fromBytes(
      base64Decode(
        (job['manifest_base64'] ?? fixture['manifest_base64']) as String,
      ),
    );
    final cache = CacheNamespace.forTarget(
      'https://independent.invalid',
      manifest.target,
    );
    final inputs = (job['objects'] ?? <dynamic>[]) as List;
    if (job['action'] == 'manifest') {
      stdout.writeln(
        jsonEncode({'ok': true, 'bytes': base64Encode(manifest.bytes)}),
      );
      return;
    }
    if (job['action'] == 'verify') {
      final results = <Map<String, dynamic>>[];
      for (final item in inputs) {
        try {
          final obj = VerifiedObject.verify(
            base64Decode(item['data_base64'] as String),
            ObjectRef.parse(item['ref']),
            cache,
          );
          results.add({
            'ok': true,
            'kind': obj.kind,
            'bytes': base64Encode(obj.bytes),
          });
        } catch (error) {
          results.add({'ok': false, 'error': '$error'});
        }
      }
      stdout.writeln(jsonEncode({'ok': true, 'results': results}));
      return;
    }
    final configured = job['limits'] as Map<String, dynamic>? ?? {};
    final limits = ClientStoreLimits(
      objectCount: configured['objectCount'] as int? ?? 100000,
      objectBytes: configured['objectBytes'] as int? ?? 67108864,
      totalObjectBytes: configured['totalObjectBytes'] as int? ?? 536870912,
      manifestBytes: configured['manifestBytes'] as int? ?? 8388608,
      metadataBytes: configured['metadataBytes'] as int? ?? 33554432,
      stagingCount: configured['stagingCount'] as int? ?? 128,
      databasePages: configured['databasePages'] as int? ?? 262144,
      busyMilliseconds: configured['busyMilliseconds'] as int? ?? 1000,
    );
    final opening = Stopwatch()..start();
    store = SegmentedClientStore.open(
      Directory(job['root'] as String),
      cache,
      limits: limits,
      fault: (point) {
        if (point == job['kill_at']) {
          stdout.writeln(jsonEncode({'ready': point}));
          stdin.readLineSync();
        }
      },
    );
    if (job['barrier'] == true) {
      stdout.writeln(jsonEncode({'ready': 'opened'}));
      stdin.readLineSync();
    }
    final result = <String, dynamic>{'ok': true, 'path': store.path};
    result['open_us'] = opening.elapsedMicroseconds;
    switch (job['action']) {
      case 'open':
        break;
      case 'put':
        for (final item in inputs) {
          store.putVerifiedObject(
            ObjectRef.parse(item['ref']),
            base64Decode(item['data_base64'] as String),
          );
        }
        result['count'] = store.listStoredObjectIdentities(limit: 1024).length;
        break;
      case 'read':
        result['results'] = [
          for (final item in inputs)
            store.getVerifiedObject(ObjectRef.parse(item['ref']))?.bytes == null
                ? null
                : base64Encode(
                    store
                        .getVerifiedObject(ObjectRef.parse(item['ref']))!
                        .bytes,
                  ),
        ];
        break;
      case 'stage':
        final stage = store.createStaging(
          job['id'] as String,
          manifest,
          DateTime.utc(2026, 10, 12),
        );
        result['state'] = stage.validationState;
        break;
      case 'progress':
        for (final item in inputs) {
          store.recordStagedObject(
            job['id'] as String,
            ObjectRef.parse(item['ref']),
          );
        }
        break;
      case 'load_stage':
        final stage = store.loadStaging(job['id'] as String);
        result['stage'] = stage == null
            ? null
            : {
                'state': stage.validationState,
                'count': stage.objectCount,
                'manifest': base64Encode(stage.manifest.bytes),
              };
        break;
      case 'cleanup':
        result['removed'] = store.removeUnreferencedStagingData(
          job['id'] as String,
        );
        break;
      case 'health':
        final health = store.inspectStoreHealth();
        result['healthy'] = health.healthy;
        result['issues'] = health.issues;
        break;
      case 'benchmark':
        for (final item in inputs) {
          store.putVerifiedObject(
            ObjectRef.parse(item['ref']),
            base64Decode(item['data_base64'] as String),
          );
        }
        final ref = ObjectRef.parse(inputs.first['ref']);
        final raw = base64Decode(inputs.first['data_base64'] as String);
        final reading = Stopwatch()..start();
        for (var i = 0; i < 200; i++) {
          store.getVerifiedObject(ref);
        }
        result['get_mean_us'] = reading.elapsedMicroseconds / 200;
        final writing = Stopwatch()..start();
        for (var i = 0; i < 100; i++) {
          store.putVerifiedObject(ref, raw);
        }
        result['duplicate_put_mean_us'] = writing.elapsedMicroseconds / 100;
        result['sqlite'] = sqlite3.version.toString();
        result['rss_bytes'] = ProcessInfo.currentRss;
        result['max_rss_bytes'] = ProcessInfo.maxRss;
        break;
      default:
        throw StateError('unknown audit operation');
    }
    stdout.writeln(jsonEncode(result));
  } on SegmentedException catch (error) {
    stdout.writeln(
      jsonEncode({
        'ok': false,
        'error': error.code,
        'storageCode': error.storageCode,
      }),
    );
  } catch (error) {
    stdout.writeln(jsonEncode({'ok': false, 'unexpected': '$error'}));
  } finally {
    store?.close();
  }
}
