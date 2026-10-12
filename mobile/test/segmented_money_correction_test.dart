import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_fixture.dart';

Map<String, dynamic> settingBody(ServerGolden golden, String text,
        {String key = 'scheduled_income'}) =>
    {
      'kind': 'snapshot-leaf',
      'ns': golden.manifest.target.ns.toJson(),
      'canon': 1,
      'raw_schema': golden.manifest.target.versions.rawSchema,
      'table': 'app_settings',
      'height': 0,
      'count': '1',
      'min': ['t', key],
      'max': ['t', key],
      'oversized': false,
      'rows': [
        {
          'key': ['t', key],
          'value': {'key': key, 'value': text, 'updated_at': '한글 😀 e\u0301'}
        }
      ]
    };

void main() {
  final golden = ServerGolden();
  final fixture = jsonDecode(
          File('test/fixtures/segmented_money_vectors.json').readAsStringSync())
      as Map;
  for (final vector in fixture['vectors'] as List) {
    test('server/Dart monetary differential ${vector['id']}', () {
      final text = vector['value'] as String;
      final raw = encodeC1(settingBody(golden, text));
      final ref = ObjectRef.parse(vector['ref']);
      // The expected identity and boolean come from the actual Python server.
      expect('${raw.length}', ref.bytes);
      expect(
          sha256.convert([
            ...ascii.encode('money-note.sync.v1/snapshot-leaf'),
            0,
            ...raw
          ]).toString(),
          ref.hash);
      if (vector['accepted'] == false) {
        expect(() => VerifiedObject.verify(raw, ref, golden.cache),
            throwsA(isA<SegmentedException>()));
        return;
      }
      final directory = Directory.systemTemp.createTempSync('e1-money-');
      SegmentedClientStore? store;
      try {
        store = SegmentedClientStore.open(directory, golden.cache);
        store.putVerifiedObject(ref, raw);
        final path = store.path;
        store.close();
        store = SegmentedClientStore.open(directory, golden.cache);
        final restored = store.getVerifiedObject(ref)!;
        expect(restored.bytes, raw);
        expect(restored.body['rows'][0]['value']['value'], text);
        final direct = sqlite3.open(path);
        try {
          expect(direct.select('SELECT body FROM objects').single['body'], raw);
          expect(direct.select('SELECT count(*) AS n FROM objects').single['n'],
              1);
        } finally {
          direct.close();
        }
      } finally {
        store?.close();
        directory.deleteSync(recursive: true);
      }
    });
  }
  test('all five monetary settings use the same server whitespace semantics',
      () {
    for (final key in [
      'scheduled_income',
      'cash_flow_balance',
      'card_limit',
      'base_next_month_liquidity',
      'liquidity_status'
    ]) {
      for (final text in [
        '\u001c+0001000.00\u001f',
        '\ufeff1000',
        '10\ufeff00',
        '1000\ufeff'
      ]) {
        final raw = encodeC1(settingBody(golden, text, key: key));
        final ref = refFor('snapshot-leaf', raw);
        if (text.startsWith('\u001c')) {
          expect(
              VerifiedObject.verify(raw, ref, golden.cache).body['rows'][0]
                  ['value']['value'],
              text);
        } else {
          expect(() => VerifiedObject.verify(raw, ref, golden.cache),
              throwsA(isA<SegmentedException>()));
        }
      }
    }
  });
}
