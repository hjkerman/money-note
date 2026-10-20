import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../docs/benchmarks/t66f-b02-implementation/verification_profile.dart';
import 'support/segmented_fixture.dart';

void main() {
  final golden = ServerGolden();
  late Directory root;
  late SegmentedClientStore store;
  var armed = false;
  void Function()? progressEvent;
  setUp(() {
    armed = false;
    progressEvent = null;
    root = Directory.systemTemp.createTempSync('mn-b02-batch-');
    store = SegmentedClientStore.open(root, golden.cache,
        acquisition: true,
        limits: largeVerificationStoreLimits, fault: (point) {
      if (point == 'after_progress_insert') progressEvent?.call();
      if (armed && point == 'after_progress_insert') {
        throw const SegmentedException('INJECTED_BATCH_FAILURE');
      }
    });
    store.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
  });
  tearDown(() {
    store.close();
    root.deleteSync(recursive: true);
  });
  Matcher code(String name) =>
      isA<SegmentedException>().having((e) => e.code, 'code', name);
  void rows(int objects, int progress) {
    final db = sqlite3.open(store.path);
    try {
      expect(
          db.select('SELECT count(*) AS n FROM objects').single['n'], objects);
      expect(db.select('SELECT count(*) AS n FROM staging_objects').single['n'],
          progress);
      expect(db.select('PRAGMA foreign_key_check'), isEmpty);
      db.execute('BEGIN IMMEDIATE');
      db.execute('ROLLBACK');
    } finally {
      db.close();
    }
  }

  final control = golden.ref('control'), bytes = golden.bytes('control');

  for (final n in [0, 64, 65]) {
    test(
        'B02 actual batch item boundary $n; durable rows independently checked',
        () {
      void action() => store.putVerifiedStagedBatch(
          stageId, List.generate(n, (_) => (ref: control, bytes: bytes)));
      if (n == 64) {
        action();
        rows(1, 1);
      } else {
        expect(action, throwsA(code('LOCAL_BATCH_BUDGET')));
        rows(0, 0);
      }
    });
  }
  ({ObjectRef ref, List<int> bytes}) leaf(int length) {
    final item = golden.objects.firstWhere((e) => e['kind'] == 'snapshot-leaf');
    final body =
        decodeC1(base64Decode(item['data_base64'])) as Map<String, dynamic>;
    final row = (body['rows'] as List).first as Map;
    body['rows'] = [row];
    body['count'] = '1';
    body['min'] = row['key'];
    body['max'] = row['key'];
    body['oversized'] = true;
    (row['value'] as Map)['title'] = '';
    final prefix = encodeC1(body).length;
    (row['value'] as Map)['title'] = 'x' * (length - prefix);
    final raw = encodeC1(body);
    expect(raw.length, length);
    return (ref: refFor('snapshot-leaf', raw), bytes: raw);
  }

  for (final length in [524288, 524289]) {
    test('B02 actual canonical batch bytes ${length * 2}', () {
      final object = leaf(length);
      void action() => store.putVerifiedStagedBatch(stageId, [object, object]);
      if (length == 524288) {
        action();
        rows(1, 1);
      } else {
        expect(action, throwsA(code('LOCAL_BATCH_BUDGET')));
        rows(0, 0);
      }
    });
  }
  test('B02 oversized valid singleton uses unchanged individual object cap',
      () {
    final object = leaf(1048577);
    store.putVerifiedStagedBatch(stageId, [object]);
    rows(1, 1);
  });
  for (final n in [2, 3]) {
    test('B02 cached object bytes are included in batch envelope: $n', () {
      final object = leaf(524288);
      store.putVerifiedObject(object.ref, object.bytes);
      void action() => store.putVerifiedStagedBatch(
          stageId, List.generate(n, (_) => (ref: object.ref, bytes: null)));
      if (n == 2) {
        action();
        rows(1, 1);
      } else {
        expect(action, throwsA(code('LOCAL_BATCH_BUDGET')));
        rows(1, 0);
      }
    });
  }
  test('B02 transaction owns refs even if fault hook mutates caller list', () {
    final entries = <({ObjectRef ref, List<int>? bytes})>[
      (ref: control, bytes: bytes),
      (ref: golden.ref('hot'), bytes: golden.bytes('hot'))
    ];
    progressEvent = entries.clear;
    store.putVerifiedStagedBatch(stageId, entries);
    expect(entries, isEmpty);
    rows(2, 2);
  });
  test('B02 batch progress failure rolls back every new object/link', () {
    store.putVerifiedObject(control, bytes);
    armed = true;
    final object = leaf(524288);
    expect(
        () => store.putVerifiedStagedBatch(
            stageId, [(ref: control, bytes: null), object]),
        throwsA(code('INJECTED_BATCH_FAILURE')));
    rows(1, 0);
    expect(store.getVerifiedObject(control)!.bytes, bytes);
  });
  test('B02 a missing cached member rolls back earlier new member', () {
    expect(
        () => store.putVerifiedStagedBatch(stageId, [
              (ref: control, bytes: bytes),
              (ref: golden.ref('raw-root'), bytes: null)
            ]),
        throwsA(code('OBJECT_MISSING')));
    rows(0, 0);
  });
  test('B02 corrupt member rejects the whole batch before transaction', () {
    final bad = List<int>.from(bytes)..[0] = 0;
    expect(
        () => store.putVerifiedStagedBatch(stageId,
            [(ref: control, bytes: bytes), (ref: control, bytes: bad)]),
        throwsA(isA<SegmentedException>()));
    rows(0, 0);
  });
  test('B02 cached progress is idempotent and immutable data remains verified',
      () {
    store.putVerifiedStagedBatch(stageId, [(ref: control, bytes: bytes)]);
    expect(store.isStagedObject(stageId, control), isTrue);
    store.putVerifiedStagedBatch(stageId, [(ref: control, bytes: null)]);
    rows(1, 1);
    expect(store.inspectStoreHealth().healthy, isTrue);
  });
}
