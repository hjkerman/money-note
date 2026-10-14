// 새 corpus의 기대 결과는 Python backend와 별도 pre-P0 Dart process가 만든다.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';

bool accepts(void Function() f) {
  try {
    f();
    return true;
  } on FormatException {
    return false;
  }
}

void main(List<String> args) {
  final corpus = jsonDecode(File(args[0]).readAsStringSync()) as Map;
  final old = jsonDecode(File(args[1]).readAsStringSync()) as List;
  final golden = jsonDecode(File(args[2]).readAsStringSync()) as Map;
  final manifest = ObservationManifest.fromBytes(
    base64Decode(golden['manifest_base64']),
  );
  final cache = CacheNamespace.forTarget(
    'https://independent-p0.synthetic',
    manifest.target,
  );
  final mismatches = <String, List<int>>{
    'authoritative': [],
    'e1': [],
    'frozen': [],
    'raw': [],
    'c1_hash': [],
    'non_setting': [],
  };
  final familyCounts = <String, Map<String, int>>{};
  var accepted = 0;
  for (final raw in corpus['cases'] as List) {
    final c = raw as Map, text = c['value'] as String, key = c['key'] as String;
    final id = c['id'] as int, expected = c['accepted'] as bool;
    final settings = <String, dynamic>{key: text};
    final row = <String, dynamic>{
      'key': key,
      'value': text,
      'updated_at': '독립 합성 한글 e\u0301 😀',
    };
    final payload = <String, dynamic>{
      '한글': {
        'settings': settings,
        'app_settings': [row],
      },
    };
    final before = jsonEncode(payload);
    final outcomes = [
      accepts(() => exactAuthoritativeSettingMoney(text)),
      accepts(() => validateAuthoritativeSettingsMoney(settings)),
      accepts(() => validateAuthoritativeMoneyPayload(payload)),
      accepts(() => AppSettings.fromJson(settings)),
    ];
    if (outcomes.any((v) => v != expected))
      mismatches['authoritative']!.add(id);
    if (expected) {
      accepted++;
      if (exactAuthoritativeSettingMoney(text) != c['amount'])
        mismatches['authoritative']!.add(id);
      if (AppSettings.fromJson(settings).values[key] != text)
        mismatches['raw']!.add(id);
    }
    if (jsonEncode(payload) != before) mismatches['raw']!.add(id);
    final bytes = base64Decode(c['data_base64']);
    bool e1 = true;
    try {
      final object = VerifiedObject.verify(
        bytes,
        ObjectRef.parse(c['ref']),
        cache,
      );
      if (base64Encode(object.bytes) != c['data_base64'] ||
          object.body['rows'][0]['value']['value'] != text)
        mismatches['raw']!.add(id);
    } on SegmentedException {
      e1 = false;
    }
    if (e1 != expected) mismatches['e1']!.add(id);
    if (objectHash('snapshot-leaf', bytes) != c['ref']['hash'] ||
        base64Encode(encodeC1(decodeC1(bytes))) != c['data_base64'])
      mismatches['c1_hash']!.add(id);
    final frozen = [
      accepts(() => exactMoney(text)),
      accepts(() => validateMoneyPayload({'amount_value': text})),
      accepts(
        () => validateMoneyPayload({
          'settings': {key: text},
        }),
      ),
      accepts(
        () => OfflineJournalOperation.fromJson({
          'schema_version': 1,
          'operation_id': 'independent-$id',
          'operation_type': 'CREATE_CASH_FLOW',
          'payload': {
            'amount_value': text,
            'settings': {key: text},
          },
          'created_at': '2026-10-14T00:00:00Z',
          'sequence': id + 1,
          'status': 'pending',
        }),
      ),
    ];
    if (frozen.any((v) => v != old[id])) mismatches['frozen']!.add(id);
    if (accepts(
          () => validateAuthoritativeMoneyPayload({'amount_value': text}),
        ) !=
        old[id]) {
      mismatches['non_setting']!.add(id);
    }
    final counts = familyCounts.putIfAbsent(
      c['family'],
      () => {'accepted': 0, 'rejected': 0},
    );
    final state = expected ? 'accepted' : 'rejected';
    counts[state] = counts[state]! + 1;
  }
  stdout.writeln(
    jsonEncode({
      'cases': (corpus['cases'] as List).length,
      'accepted': accepted,
      'rejected': (corpus['cases'] as List).length - accepted,
      'mismatches': mismatches,
      'frozen_accepted': old.where((v) => v == true).length,
      'families': familyCounts,
    }),
  );
}
