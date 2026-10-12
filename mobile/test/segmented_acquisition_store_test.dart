import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_fixture.dart';

void main() {
  final golden = ServerGolden();
  late Directory root;
  SegmentedClientStore? store;
  setUp(() =>
      root = Directory.systemTemp.createTempSync('money-note-e2-schema-'));
  tearDown(() {
    store?.close();
    root.deleteSync(recursive: true);
  });
  SegmentedClientStore open({StoreFault? fault, bool acquisition = true}) =>
      store = SegmentedClientStore.open(root, golden.cache,
          acquisition: acquisition, fault: fault);
  test('exact v1 migrates ONLY by opt-in; prior object/staging bytes preserved',
      () {
    var db = open(acquisition: false);
    db.putVerifiedObject(golden.ref('raw-root'), golden.bytes('raw-root'));
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
    db.close();
    db = open();
    expect(db.getVerifiedObject(golden.ref('raw-root'))!.bytes,
        golden.bytes('raw-root'));
    expect(db.loadStaging(stageId)!.manifest.bytes, golden.manifest.bytes);
    final direct = sqlite3.open(db.path);
    expect(direct.select('PRAGMA user_version').single.values.first, 2);
    expect(
        direct
            .select(
                'SELECT count(*) AS n FROM sqlite_master WHERE sql IS NOT NULL')
            .single['n'],
        23);
    direct.close();
    expect(db.inspectStoreHealth().healthy, isTrue);
  });
  test('default E1 profile does NOT reinterpret or downgrade v2', () {
    final db = open();
    db.close();
    expect(() => open(acquisition: false), throwsA(isA<SegmentedException>()));
  });
  test('damaged v1 cannot migrate or silently recreate missing trigger', () {
    final db = open(acquisition: false), path = db.path;
    db.close();
    final direct = sqlite3.open(path);
    direct.execute('DROP TRIGGER object_usage');
    direct.close();
    expect(() => open(), throwsA(isA<SegmentedException>()));
    final inspected = sqlite3.open(path);
    expect(inspected.select('PRAGMA user_version').single.values.first, 1);
    expect(
        inspected
            .select("SELECT name FROM sqlite_master WHERE name='acquisition'"),
        isEmpty);
    inspected.close();
  });
  test('bookkeeping state and error survive close/reopen; never authority', () {
    var db = open();
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
    db.recordAcquisition(stageId, 'acquiring');
    db.recordAcquisition(stageId, 'interrupted',
        errorCode: 'TRANSPORT_TIMEOUT');
    db.close();
    db = open();
    expect(db.acquisitionProgress(stageId)!.state, 'interrupted');
    expect(db.acquisitionProgress(stageId)!.errorCode, 'TRANSPORT_TIMEOUT');
    expect(db.loadStaging(stageId)!.validationState, 'staged');
  });
  for (final scenario in [
    'state',
    'missing_error',
    'unexpected_error',
    'sensitive_error',
    'missing_stage'
  ]) {
    test('invalid progress $scenario cannot COMMIT', () {
      final db = open();
      db.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
      final state = scenario == 'state'
          ? 'active'
          : scenario == 'missing_error'
              ? 'interrupted'
              : 'acquiring';
      final error = scenario == 'unexpected_error'
          ? 'FAILED'
          : scenario == 'sensitive_error'
              ? 'raw secret financial text'
              : null;
      expect(
          () => db.recordAcquisition(
              scenario == 'missing_stage'
                  ? 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
                  : stageId,
              state,
              errorCode: error),
          throwsA(isA<SegmentedException>()));
      final direct = sqlite3.open(db.path);
      expect(direct.select('SELECT * FROM acquisition'), isEmpty);
      direct.close();
    });
  }
  for (final trigger in [
    'acquisition_usage',
    'acquisition_release',
    'object_usage'
  ]) {
    test('missing v2 trigger $trigger prevents affected writes BEFORE COMMIT',
        () {
      final db = open();
      db.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
      final direct = sqlite3.open(db.path);
      direct.execute('DROP TRIGGER $trigger');
      direct.close();
      expect(() => db.recordAcquisition(stageId, 'acquiring'),
          throwsA(isA<SegmentedException>()));
      final inspected = sqlite3.open(db.path);
      expect(inspected.select('SELECT * FROM acquisition'), isEmpty);
      expect(
          inspected.select('SELECT count(*) AS n FROM staging').single['n'], 1);
      inspected.close();
    });
  }
  test('failed metadata transaction rolls back to previous progress', () {
    var inject = false;
    final db = open(fault: (point) {
      if (inject && point == 'after_acquisition_insert') {
        throw const SegmentedException('INJECTED_FAILURE');
      }
    });
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
    db.recordAcquisition(stageId, 'acquiring');
    inject = true;
    expect(() => db.recordAcquisition(stageId, 'graph_verified'),
        throwsA(isA<SegmentedException>()));
    expect(db.acquisitionProgress(stageId)!.state, 'acquiring');
    final direct = sqlite3.open(db.path);
    expect(direct.select('SELECT state FROM acquisition').single['state'],
        'acquiring');
    direct.execute('BEGIN IMMEDIATE');
    direct.execute('ROLLBACK');
    direct.close();
  });
  test(
      'explicit staging cleanup reclaims bounded bookkeeping, NOT object cache',
      () {
    final db = open();
    db.putVerifiedObject(golden.ref('raw-root'), golden.bytes('raw-root'));
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
    db.recordAcquisition(stageId, 'graph_verified');
    final direct = sqlite3.open(db.path);
    expect(
        direct.select('SELECT count(*) AS n FROM acquisition').single['n'], 1);
    db.removeUnreferencedStagingData(stageId);
    expect(
        direct.select('SELECT count(*) AS n FROM acquisition').single['n'], 0);
    direct.close();
    expect(db.getVerifiedObject(golden.ref('raw-root')), isNotNull);
    expect(db.inspectStoreHealth().healthy, isTrue);
  });
}
