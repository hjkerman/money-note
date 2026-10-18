// 조사 전용: read-only backend export 또는 새 disposable E1 store만 사용한다.
// 제품 한도 변경, accepted pointer 삽입, HTTP integration 대체는 하지 않는다.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/lib/src/segmented/c1.dart';
import '../../../mobile/lib/src/segmented/graph.dart';
import '../../../mobile/lib/src/segmented/object.dart';
import '../../../mobile/lib/src/segmented/protocol.dart';
import '../../../mobile/lib/src/segmented/store.dart';
import '../../../mobile/lib/src/segmented/verification.dart';

Future<void> main(List<String> args) async {
  final mode = args[0], dir = args[1];
  final manifest = ObservationManifest.fromBytes(
    File('$dir/manifest-g1.json').readAsBytesSync(),
  );
  final target = manifest.target;
  final cache = CacheNamespace.forTarget(
    'https://synthetic-b02.invalid',
    target,
  );
  final db = sqlite3.open('$dir/objects.sqlite', mode: OpenMode.readOnly);
  var reads = 0, bytes = 0;
  final clock = Stopwatch()..start();
  final result = <String, dynamic>{
    'mode': mode,
    'input': dir,
    'http_executed': false,
    'accepted_publication': false,
    'limits_modified': false,
    'rss_start': ProcessInfo.currentRss,
  };
  VerifiedObject load(ObjectRef ref) {
    final body =
        db.select('SELECT body FROM sync_objects WHERE hash=?', [
              ref.hash,
            ]).single['body']
            as Uint8List;
    reads++;
    bytes += body.length;
    return VerifiedObject.verify(body, ref, cache);
  }

  try {
    if (mode == 'graph' || mode == 'boundary') {
      final graph = await verifyAcquisitionGraph(
        target,
        (edge, _) async => load(edge.ref),
        maxObjects: 100000,
        maxEdges: 200000,
      );
      result.addAll({
        'status': 'PASS',
        'objects': graph.objects.length,
        'edges': graph.edges,
        'cold_us': clock.elapsedMicroseconds,
        'rss_after_cold': ProcessInfo.currentRss,
        'cold_reads': reads,
        'cold_body_bytes': bytes,
      });
      final previous = reads;
      final repeatClock = Stopwatch()..start();
      final repeated = await verifyAcquisitionGraph(
        target,
        (edge, _) async => load(edge.ref),
        maxObjects: 100000,
        maxEdges: 200000,
        reuse: graph.provenance,
      );
      result.addAll({
        'repeat_reads': reads - previous,
        'repeat_us': repeatClock.elapsedMicroseconds,
        'repeat_objects': repeated.objects.length,
      });
      if (mode == 'boundary') {
        final v = graph.objects.length;
        final outcomes = <String, dynamic>{};
        for (final bound in [v - 1, v, v + 1]) {
          for (final reused in [false, true]) {
            final start = reads;
            String status;
            try {
              await verifyAcquisitionGraph(
                target,
                (edge, _) async => load(edge.ref),
                maxObjects: bound,
                maxEdges: 200000,
                reuse: reused ? graph.provenance : null,
              );
              status = 'PASS';
            } on SegmentedException catch (e) {
              status = e.code;
            }
            outcomes['$bound/$reused'] = {
              'status': status,
              'reads': reads - start,
            };
            if (status != (bound < v ? 'GRAPH_OBJECT_BUDGET' : 'PASS'))
              throw StateError('boundary oracle');
          }
        }
        result['boundary'] = outcomes;
      }
    } else if (mode == 'facts' || mode == 'simulation') {
      // 실제 E3 공개 component의 offline 실행. E2 cap 우회나 CompleteProof가 아니다.
      final summaries = <String, List<Object?>>{};
      if (mode == 'simulation') {
        final frontier = target.roots.values.toList();
        while (frontier.isNotEmpty) {
          final ref = frontier.removeLast();
          if (summaries.containsKey(ref.hash)) continue;
          if (summaries.length >= 600000)
            throw StateError('offline simulation bound');
          final obj = load(ref), body = obj.body;
          final prefix = body['prefix'] ?? body['digest'] ?? '';
          summaries[ref.hash] = [
            ref,
            obj.kind,
            obj.children,
            body['count'],
            body['table'],
            prefix,
            <String, String>{},
          ];
          frontier.addAll(obj.children.map((e) => e.ref));
        }
        result['simulation_summary_objects'] = summaries.length;
        result['rss_summaries'] = ProcessInfo.currentRss;
        result['simulation_not_complete_generation_proof'] = true;
      }
      final data = <String, dynamic>{
        for (final table in segmentedTables) table: <Map<String, dynamic>>[],
      };
      final pending = [target.roots['raw']!];
      while (pending.isNotEmpty) {
        final obj = load(pending.removeLast());
        final b = obj.body;
        if (obj.kind == 'snapshot-leaf') {
          (data[b['table']] as List).addAll(
            (b['rows'] as List).map<Map<String, dynamic>>(
              (r) => Map<String, dynamic>.from(r['value']),
            ),
          );
        }
        pending.addAll(obj.children.map((e) => e.ref));
      }
      result['rows'] = data.values.fold<int>(
        0,
        (n, rows) => n + (rows as List).length,
      );
      result['rss_raw'] = ProcessInfo.currentRss;
      final facts = buildRawFacts(target, data);
      result['facts'] = facts.length;
      result['rss_facts'] = ProcessInfo.currentRss;
      final actual = canonicalFactsRoot(target, facts.values);
      if (!actual.matches(target.roots['index']!))
        throw StateError('independent backend index mismatch');
      result['rss_after_root'] = ProcessInfo.currentRss;
      result['retained_summary_objects_after_facts'] = summaries.length;
      result['status'] = 'PASS';
    } else if (mode == 'store' || mode == 'sample') {
      final root = Directory(args[2]);
      final store = SegmentedClientStore.open(root, cache, acquisition: true);
      const staging = '66260200-0000-4000-8000-000000000001';
      store.createStaging(staging, manifest, DateTime.utc(2026, 10, 17));
      result['store_directory'] = root.path;
      var inserted = 0;
      final pending = target.roots.values.toList();
      final seen = <String>{};
      String? rejected;
      while (pending.isNotEmpty) {
        if (mode == 'sample' && inserted >= 1000) break;
        final ref = pending.removeLast();
        if (!seen.add(ref.hash)) continue;
        final obj = load(ref);
        try {
          store.putVerifiedObject(ref, obj.bytes);
          inserted++;
          store.recordStagedObject(staging, ref);
        } on SegmentedException catch (e) {
          rejected = e.code;
          break;
        }
        pending.addAll(obj.children.reversed.map((e) => e.ref));
      }
      result['put_and_progress_us'] = clock.elapsedMicroseconds;
      if (mode == 'sample') {
        final refs = store.listStoredObjectIdentities(limit: 1000);
        final timings = <String, int>{};
        for (final reuseStage in [true, false]) {
          final id = reuseStage
              ? staging
              : '66260200-0000-4000-8000-000000000002';
          store.createStaging(id, manifest, DateTime.utc(2026, 10, 17));
          final timer = Stopwatch()..start();
          for (final ref in refs) {
            if (store.getVerifiedObject(ref) == null)
              throw StateError('sample missing');
            store.recordStagedObject(id, ref);
          }
          timings[reuseStage ? 'existing_stage_us' : 'new_stage_us'] =
              timer.elapsedMicroseconds;
        }
        result['cached_sample'] = {'objects': refs.length, ...timings};
      }
      store.close();
      final file = root
          .listSync(recursive: true)
          .whereType<File>()
          .singleWhere((f) => f.path.endsWith('.sqlite'));
      final inspect = sqlite3.open(file.path, mode: OpenMode.readOnly);
      result.addAll({
        'status': rejected ?? 'PASS',
        'inserted': inserted,
        'durable_usage': inspect
            .select('SELECT * FROM usage')
            .map((r) => Map<String, Object?>.from(r))
            .toList(),
        'objects_sql': inspect
            .select(
              'SELECT count(*) AS n,sum(length(body)) AS bytes FROM objects',
            )
            .map((r) => Map<String, Object?>.from(r))
            .toList(),
        'database_bytes': file.lengthSync(),
        'page_count': inspect.select('PRAGMA page_count').single.values.first,
        'page_size': inspect.select('PRAGMA page_size').single.values.first,
      });
      inspect.dispose();
    } else {
      throw ArgumentError(mode);
    }
  } on SegmentedException catch (e) {
    result['status'] = e.code;
  } finally {
    result.addAll({
      'wall_us': clock.elapsedMicroseconds,
      'actual_loader_reads': reads,
      'actual_loader_body_bytes': bytes,
      'rss_end': ProcessInfo.currentRss,
      'peak_rss': ProcessInfo.maxRss,
      'sqlite_version': sqlite3.version.toString(),
    });
    db.dispose();
    File(args.last).writeAsStringSync(
      '${const JsonEncoder.withIndent('  ').convert(result)}\n',
    );
    stdout.writeln(
      jsonEncode({'mode': mode, 'input': dir, 'status': result['status']}),
    );
  }
}
