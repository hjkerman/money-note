// 같은 actual synthetic wire를 교정 전/후 package에 각각 전달한다.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';

void main(List<String> args) {
  final evidence = jsonDecode(File(args.single).readAsStringSync()) as Map;
  final wire = evidence['wire'] as Map<String, dynamic>;
  final baseline = <String, dynamic>{
    ...wire['state'] as Map<String, dynamic>,
    'schema_version': 4,
    'synced_at': wire['snapshot']['exported_at'],
    'user': {
      'id': 1,
      'username': 'synthetic',
      'display_name': '독립 합성',
      'share_pin_needs_change': false,
    },
    'authoritative_snapshot': wire['snapshot'],
    'server_state_fingerprint': wire['authority']['state_fingerprint'],
    'resolved_reconciliation_id': null,
    'discount_policy_defaults': wire['authority']['discount_policy_defaults'],
  };
  bool accepts(void Function() f) {
    try {
      f();
      return true;
    } on FormatException {
      return false;
    }
  }

  final before = jsonEncode(wire);
  stdout.writeln(
    jsonEncode({
      'bundle': accepts(() => AuthoritativeBundle.decode(utf8.encode(before))),
      'baseline': accepts(() => OfflineBaseline.fromJson(baseline)),
      'legacy_input': accepts(() => exactMoney('\u001c+0001000.00\u001f')),
      'wire_unchanged': jsonEncode(wire) == before,
      'source_codepoints':
          (wire['state']['settings']['cash_flow_balance'] as String).runes
              .toList(),
    }),
  );
}
