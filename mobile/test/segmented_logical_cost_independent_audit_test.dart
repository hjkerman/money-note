// 독립 oracle/결함 재현. 재현 테스트 PASS를 계측 정확성 PASS로 해석하지 않는다.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/logical_cost_sqlite.dart';
import 'support/offline_mode_fixtures.dart';

final auditOut = Directory(
    '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-independent/evidence');
void evidence(String name, Object value) {
  auditOut.createSync(recursive: true);
  File('${auditOut.path}/$name.json').writeAsStringSync(jsonEncode(value));
}

class SyntheticBaseline implements OfflineBaseline {
  SyntheticBaseline(this.json);
  final Map<String, dynamic> json;
  int calls = 0;
  @override
  Map<String, dynamic> toJson() {
    calls++;
    return json;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('audit');
}

// da818648의 recoveryLineageFingerprint 및 canonical helper 본문을 보존한 oracle.
// 원문 및 SHA는 evidence/historical-lineage-source.json에서 대조한다.
String historicalFingerprint(OfflineBaseline baseline) {
  return sha256
      .convert(utf8.encode(historicalJson({
        'schema_version': 1,
        'origin': 'mobile-baseline-lineage',
        'baseline': baseline.toJson(),
      })))
      .toString();
}

String historicalJson(Object? value) => jsonEncode(historicalValue(value));
Object? historicalValue(Object? value) {
  if (value is Map) {
    final keys = value.keys.map((key) => key.toString()).toList()..sort();
    return <String, Object?>{
      for (final key in keys) key: historicalValue(value[key]),
    };
  }
  if (value is List) return value.map(historicalValue).toList();
  return value;
}

BigInt sql(SqlCosts s, String key) => s.values[key] ?? BigInt.zero;

void main() {
  final goldens = jsonDecode(
      File('${auditOut.parent.path}/lineage-goldens.json')
          .readAsStringSync()) as List;
  for (var i = 0; i < goldens.length; i++) {
    test('independent historical P0 exact bytes fixture $i', () {
      final golden = goldens[i] as Map;
      final b = SyntheticBaseline(
          (golden['baseline'] as Map).cast<String, dynamic>());
      final c = LogicalCost(), store = OfflineStore();
      final old = historicalFingerprint(b);
      final disabled = store.recoveryLineageFingerprint(b);
      final enabled = c.run(
          LogicalCostStage.recovery, () => store.recoveryLineageFingerprint(b));
      expect(utf8.encode(old), utf8.encode(golden['sha256'] as String));
      expect(utf8.encode(enabled), utf8.encode(old));
      expect(utf8.encode(disabled), utf8.encode(old));
      expect(b.calls, 3, reason: '역사/비활성/활성 각각 한 번');
      expect(c.snapshot(), {
        'recovery/lineageHash/calls': '1',
        'recovery/lineageHash/hashInputBytes': '${golden['bytes']}'
      });
    });
  }

  test('independent existing compatibility baseline matches historical P0', () {
    for (final b in [
      baselineFixture(),
      baselineFixture(includeAuthority: false),
      baselineFixture(registeredCandidate: true),
      baselineFixture(legacyRegisteredCandidate: true)
    ]) {
      final expected = historicalFingerprint(b), c = LogicalCost();
      final off = OfflineStore().recoveryLineageFingerprint(b);
      final on = c.run(LogicalCostStage.recovery,
          () => OfflineStore().recoveryLineageFingerprint(b));
      expect(utf8.encode(off), utf8.encode(expected));
      expect(utf8.encode(on), utf8.encode(expected));
    }
  });

  test('independent yielded late completion cannot mutate closed owner',
      () async {
    final a = LogicalCost(), b = LogicalCost();
    final started = Completer<void>(), release = Completer<void>();
    final late = a.run(LogicalCostStage.e2, () async {
      localChecksum([1, 2, 3]);
      started.complete();
      await release.future;
      localChecksum(List.filled(77, 1));
      throw StateError('independent late exception');
    });
    final observed = expectLater(late, throwsStateError);
    await started.future;
    a.close();
    final frozen = a.snapshot();
    await b.run(LogicalCostStage.e3Verify, () async {
      localChecksum(List.filled(11, 1));
      release.complete();
      await observed;
      b.run(LogicalCostStage.e4Read, () => localChecksum([1]));
    });
    expect(a.snapshot(), frozen);
    expect(b.snapshot()['e3Verify/checksum/hashInputBytes'], '11');
    expect(b.snapshot()['e4Read/checksum/hashInputBytes'], '1');
    expect(LogicalCost.activeCollector, isNull);
    evidence('async-late-independent', {'closed': frozen, 'new': b.snapshot()});
  });

  for (final mode in ['duplicate-savepoint', 'or-fail', 'comment-insert']) {
    test('independent SQL defect reproducer $mode', () {
      final c = LogicalCost(), s = SqlCosts();
      final native = sqlite3.openInMemory();
      final d = CostDatabase(native, s);
      try {
        d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
        c.run(LogicalCostStage.e1, () {
          if (mode == 'duplicate-savepoint') {
            for (final statement in [
              'BEGIN',
              'SAVEPOINT s',
              "INSERT INTO payload VALUES ('a',x'01')",
              'SAVEPOINT s',
              "INSERT INTO payload VALUES ('b',x'0203')",
              'ROLLBACK TO s',
              'RELEASE s',
              'COMMIT'
            ]) {
              d.execute(statement);
            }
          } else if (mode == 'or-fail') {
            d.execute('BEGIN');
            d.execute("INSERT INTO payload VALUES ('prior',x'01')");
            expect(
                () => d.execute(
                    "INSERT OR FAIL INTO payload VALUES ('a',x'0203'),('prior',x'040506')"),
                throwsA(isA<SqliteException>()));
            d.execute('COMMIT');
          } else {
            d.execute(
                "/* independent */ INSERT INTO payload VALUES ('a',x'0102')");
          }
        });
        // wrapper를 경유하지 않는 native DB 조회를 독립 oracle로 사용한다.
        final rows =
            native.select('SELECT k,length(b) n FROM payload ORDER BY k');
        final expected =
            rows.fold<int>(0, (sum, row) => sum + (row['n'] as int));
        final actual = sql(s, 'e1/payload/INSERT/blobBytes/committed');
        expect(
            expected,
            mode == 'duplicate-savepoint'
                ? 1
                : mode == 'or-fail'
                    ? 3
                    : 2);
        expect(actual, BigInt.from(mode == 'or-fail' ? 1 : 0));
        expect(actual, isNot(BigInt.from(expected)), reason: '확정 계측 결함 재현');
        evidence('finding-$mode-flutter', {
          'oracle_rows': rows.map((r) => r.values.toList()).toList(),
          'expected_committed': expected,
          'actual_committed': actual.toString(),
          'counters': s.snapshot()
        });
      } finally {
        d.close();
      }
    });
  }

  test('independent SQL supported nested rollback, update, receipt, pin', () {
    final c = LogicalCost(), s = SqlCosts();
    final d = CostDatabase(sqlite3.openInMemory(), s);
    try {
      c.run(LogicalCostStage.e3Commit, () {
        d.execute('CREATE TABLE receipt(k TEXT PRIMARY KEY,v BLOB)');
        d.execute('CREATE TABLE pin(k TEXT PRIMARY KEY)');
        d.execute('BEGIN');
        d.execute('INSERT INTO receipt VALUES (?,?)', [
          '한😀',
          [1, 2]
        ]);
        d.execute('SAVEPOINT outer_scope');
        d.execute('SAVEPOINT inner_scope');
        d.execute('UPDATE receipt SET v=?', [
          [1, 2, 3, 4, 5]
        ]);
        d.execute('ROLLBACK TO inner_scope');
        d.execute('RELEASE inner_scope');
        d.execute('RELEASE outer_scope');
        d.execute("INSERT INTO pin VALUES ('a')");
        d.execute("DELETE FROM pin WHERE k='a'");
        d.execute('COMMIT');
      });
      expect(sql(s, 'e3Commit/receipt/INSERT/textBytes/committed'),
          BigInt.from(7));
      expect(sql(s, 'e3Commit/receipt/INSERT/blobBytes/committed'),
          BigInt.from(2));
      expect(sql(s, 'e3Commit/receipt/UPDATE/blobBytes/rolledBack'),
          BigInt.from(5));
      expect(sql(s, 'e3Commit/pin/DELETE/effective/rows'), BigInt.one);
    } finally {
      d.close();
    }
  });

  test('independent counter category and integer bounds', () {
    final c = LogicalCost();
    for (final stage in LogicalCostStage.values) {
      c.run(stage, () {
        for (final op in LogicalCostOperation.values) {
          for (final metric in LogicalCostMetric.values) {
            LogicalCost.observe(op, metric, 9223372036854775807);
            LogicalCost.observe(op, metric, 9223372036854775807);
          }
        }
      });
    }
    expect(c.snapshot().length, 462);
    expect(c.snapshot().values.toSet(), {'18446744073709551614'});
  });

  test('independent SQLite table and savepoint capacity errors are explicit',
      () {
    final d = CostDatabase(sqlite3.openInMemory(), SqlCosts());
    try {
      for (var i = 0; i < 129; i++) {
        d.execute('CREATE TABLE t$i(a TEXT)');
      }
      expect(() => d.execute("INSERT INTO t0 VALUES ('a')"), throwsStateError);
    } finally {
      d.close();
    }
    final e = CostDatabase(sqlite3.openInMemory(), SqlCosts());
    try {
      e.execute('BEGIN');
      for (var i = 0; i < 32; i++) {
        e.execute('SAVEPOINT independent_$i');
      }
      expect(() => e.execute('SAVEPOINT exceeds_capacity'), throwsStateError);
      e.execute('ROLLBACK');
    } finally {
      e.close();
    }
  });
}
