// Investigation-only bounded component. Does NOT publish or acquire a graph.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../t66f-b02-implementation/verification_profile.dart';

void main(List<String> args) {
  final out = Directory(args.single);
  final sample = jsonDecode(
    File('${out.path}/component-sample.json').readAsStringSync(),
  ) as Map;
  final manifest = ObservationManifest.fromBytes(encodeC1(sample['manifest']));
  final cache = CacheNamespace.forTarget(
    sample['origin'] as String,
    manifest.target,
  );
  final entries = (sample['objects'] as List)
      .map(
        (v) => (
          ref: ObjectRef.parse(v['ref']),
          bytes: base64Decode(v['bytes_base64'] as String),
          kind: v['kind'] as String,
        ),
      )
      .toList();
  final total = entries.fold<int>(0, (n, e) => n + e.bytes.length);
  final hashRuns = <int>[], validationRuns = <int>[];
  for (var rep = 0; rep < 10; rep++) {
    final clock = Stopwatch()..start();
    for (final e in entries) {
      if (objectHash(e.kind, e.bytes) != e.ref.hash)
        throw StateError('hash oracle');
    }
    hashRuns.add(clock.elapsedMicroseconds);
  }
  for (var rep = 0; rep < 10; rep++) {
    final clock = Stopwatch()..start();
    for (final e in entries) {
      final v = VerifiedObject.verify(e.bytes, e.ref, cache);
      if (v.kind != e.kind || !sameBytes(v.bytes, e.bytes))
        throw StateError('canonical oracle');
    }
    validationRuns.add(clock.elapsedMicroseconds);
  }
  final writes = <Map<String, dynamic>>[];
  for (var rep = 0; rep < 3; rep++) {
    final root = Directory.systemTemp.createTempSync(
      'mn-b02-a01-e1-component-',
    );
    var commits = 0;
    final store = SegmentedClientStore.open(
      root,
      cache,
      adapters: true,
      limits: largeVerificationStoreLimits,
      fault: (p) {
        if (p == 'after_commit') commits++;
      },
    );
    final id = syncUuid();
    store.createStaging(id, manifest, DateTime.now().toUtc());
    final before = commits;
    final clock = Stopwatch()..start();
    for (var at = 0; at < entries.length; at += 64) {
      final end = (at + 64 < entries.length) ? at + 64 : entries.length;
      store.putVerifiedStagedBatch(id, [
        for (final e in entries.sublist(at, end)) (ref: e.ref, bytes: e.bytes),
      ]);
    }
    final elapsed = clock.elapsedMicroseconds;
    final db = sqlite3.open(store.path, mode: OpenMode.readOnly);
    final usage = Map<String, dynamic>.from(
      db.select('SELECT * FROM usage').single,
    );
    if (usage['objects'] != entries.length || usage['payload'] != total)
      throw StateError('durable oracle');
    if (db.select('PRAGMA foreign_key_check').isNotEmpty)
      throw StateError('FK oracle');
    final beforeRead = store.work.snapshot();
    final readClock = Stopwatch()..start();
    for (final e in entries) {
      if (!sameBytes(store.getVerifiedObject(e.ref)!.bytes, e.bytes))
        throw StateError('read oracle');
    }
    final readUs = readClock.elapsedMicroseconds;
    writes.add({
      'objects': entries.length,
      'logical_new_object_blob_bytes': total,
      'us': elapsed,
      'batch_commits': commits - before,
      'objects_per_second': entries.length * 1000000 / elapsed,
      'database_bytes': File(store.path).lengthSync(),
      'journal': db.select('PRAGMA journal_mode').single.values.first,
      'usage': usage,
      'cached_hash_on_read_us': readUs,
      'cached_read_work': store.work.since(beforeRead),
    });
    db.close();
    store.close();
    // Own new temporary component directory only; keep evidence data, no user cleanup.
  }
  File('${out.path}/e1-component.json').writeAsStringSync(
    const JsonEncoder.withIndent('  ').convert({
      'label': 'SMALL ACTUAL E1 COMPONENT; NOT COLD D-E SUCCESS',
      'objects_per_sample': entries.length,
      'bytes_per_sample': total,
      'hash_calls': entries.length * hashRuns.length,
      'logical_hash_input_bytes':
          10 *
          entries.fold<int>(
            0,
            (n, e) =>
                n +
                e.bytes.length +
                ascii.encode('money-note.sync.v1/${e.kind}').length +
                1,
          ),
      'validation_calls': entries.length * validationRuns.length,
      'logical_validation_input_bytes': 10 * total,
      'hash_us': hashRuns,
      'validation_including_hash_and_shape_us': validationRuns,
      'cold_stage_writes': writes,
      'profile': 'unchanged explicit large verification',
      'accepted_publication': 'NOT ATTEMPTED',
      'r1': 'CLOSED',
    }),
  );
  stdout.writeln(
    'E1 component: ${entries.length} objects × 3 fresh disposable stores; oracle PASS',
  );
}
