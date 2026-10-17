import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';

void main() {
  test(
    'C-P01 actual supported E2 cap cannot accommodate measured 50k graph',
    () {
      final witness = jsonDecode(
        File(const String.fromEnvironment('C_BUDGET_WITNESS'))
            .readAsStringSync(),
      );
      const supported = FetchLimits();
      supported.validate();
      expect(supported.graphObjects, witness['supported_fetch_maximum']);
      expect(
        witness['complete_generation_minimum_objects'],
        greaterThan(supported.graphObjects),
      );
      expect(
        () => const FetchLimits(graphObjects: 100001).validate(),
        throwsA(
          isA<SegmentedException>().having(
            (e) => e.code,
            'code',
            'FETCH_LIMIT_INVALID',
          ),
        ),
      );
    },
  );
  test('C-P02 exact backend/E1 authoritative money raw C1 and frozen local input separation', () {
    const raw = '\u001c+0001000.00\u001f';
    expect(exactAuthoritativeSettingMoney(raw), 1000);
    expect(() => exactMoney(raw), throwsFormatException);
    final bytes = encodeC1({'value': raw});
    expect(bytes, utf8.encode('{"value":"\\u001c+0001000.00\\u001f"}'));
    final golden = jsonDecode(
      File(const String.fromEnvironment('C_MONEY_GOLDEN')).readAsStringSync(),
    );
    expect(objectHash('row', bytes), golden['row_domain_sha256']);
    expect(raw.codeUnits, [28, 43, 48, 48, 48, 49, 48, 48, 48, 46, 48, 48, 31]);
  });
}
