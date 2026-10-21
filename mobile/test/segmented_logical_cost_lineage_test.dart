import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'support/offline_mode_fixtures.dart';

class CountedBaseline implements OfflineBaseline {
  CountedBaseline(this.inner);
  final OfflineBaseline inner;
  int serializations = 0;
  @override
  Map<String, dynamic> toJson() {
    serializations++;
    return inner.toJson();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('unexpected baseline member');
}

class FailedBaseline implements OfflineBaseline {
  @override
  Map<String, dynamic> toJson() =>
      throw const FormatException('synthetic serialization failure');
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('unexpected baseline member');
}

Future<Map> independent(OfflineBaseline baseline) async {
  final python = '${Directory.current.parent.path}/.venv/bin/python';
  final process = await Process.start(python, [
    '-c',
    'import sys,json,hashlib; b=json.load(sys.stdin); raw=json.dumps({"schema_version":1,"origin":"mobile-baseline-lineage","baseline":b},ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"); print(json.dumps({"bytes":len(raw),"fingerprint":hashlib.sha256(raw).hexdigest()}))'
  ]);
  final output = process.stdout.transform(utf8.decoder).join();
  final error = process.stderr.transform(utf8.decoder).join();
  process.stdin.write(jsonEncode(baseline.toJson()));
  await process.stdin.close();
  expect(await process.exitCode, 0, reason: await error);
  return jsonDecode(await output) as Map;
}

void main() {
  for (final unicode in [false, true]) {
    test(
        'lineage actual SHA span and disabled/enabled output match independent oracle unicode=$unicode',
        () async {
      final body = baselineFixture().toJson();
      if (unicode) {
        (body['user'] as Map)['display_name'] =
            '한😀e\u0301 \u001c+0001000.00\u001f';
      }
      final baseline = OfflineBaseline.fromJson(body);
      final expected = await independent(baseline),
          counted = CountedBaseline(baseline);
      final store = OfflineStore(), c = LogicalCost();
      final disabled = store.recoveryLineageFingerprint(counted);
      expect(counted.serializations, 1);
      final enabled = c.run(LogicalCostStage.recovery,
          () => store.recoveryLineageFingerprint(counted));
      expect(counted.serializations, 2,
          reason: 'one existing serialization per call, none for counting');
      expect(disabled.codeUnits, (expected['fingerprint'] as String).codeUnits);
      expect(enabled.codeUnits, disabled.codeUnits);
      expect(c.snapshot(), {
        'recovery/lineageHash/calls': '1',
        'recovery/lineageHash/hashInputBytes': '${expected['bytes']}'
      });
      expect(LogicalCost.activeCollector, isNull);
    });
  }

  test('lineage async stages, repeated work and closed scope stay isolated',
      () async {
    final store = OfflineStore(),
        baseline = baselineFixture(),
        a = LogicalCost(),
        b = LogicalCost();
    final expected = await independent(baseline),
        entered = Completer<void>(),
        resume = Completer<void>();
    final first = a.run(LogicalCostStage.recovery, () async {
      store.recoveryLineageFingerprint(baseline);
      entered.complete();
      await resume.future;
      store.recoveryLineageFingerprint(baseline);
    });
    await entered.future;
    b.run(LogicalCostStage.e4Read,
        () => store.recoveryLineageFingerprint(baseline));
    resume.complete();
    await first;
    expect(a.snapshot()['recovery/lineageHash/calls'], '2');
    expect(a.snapshot()['recovery/lineageHash/hashInputBytes'],
        '${2 * (expected['bytes'] as int)}');
    expect(b.snapshot()['e4Read/lineageHash/hashInputBytes'],
        '${expected['bytes']}');
    final before = a.snapshot();
    a.close();
    a.run(LogicalCostStage.e4Legacy,
        () => store.recoveryLineageFingerprint(baseline));
    expect(a.snapshot(), before);
    expect(LogicalCost.activeCollector, isNull);
  });

  test('lineage serialization exception and disabled path are unchanged', () {
    final store = OfflineStore(),
        c = LogicalCost(),
        baseline = FailedBaseline();
    expect(() => store.recoveryLineageFingerprint(baseline),
        throwsA(isA<FormatException>()));
    expect(
        () => c.run(LogicalCostStage.recovery,
            () => store.recoveryLineageFingerprint(baseline)),
        throwsA(isA<FormatException>()));
    expect(c.snapshot(), isEmpty, reason: 'no SHA input was submitted');
    expect(LogicalCost.activeCollector, isNull);
  });
}
