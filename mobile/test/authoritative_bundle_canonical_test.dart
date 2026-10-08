import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/authoritative_bundle_contract.dart';

import 'authoritative_bundle_test.dart' show parseWire, reseal, specimen;

Map<String, dynamic> corrupted(void Function(Map<String, dynamic>) mutate) {
  final wire = specimen();
  mutate(wire);
  reseal(wire);
  return wire;
}

void main() {
  final attacks = <String, void Function(Map<String, dynamic>)>{
    'A canonical classifier': (w) {
      w['snapshot']['card_charge_policy']['classifier']['matching'] = 'CORRUPT';
    },
    'A canonical selector': (w) {
      w['snapshot']['card_charge_policy']['profile_selectors']['transit']
          ['selection'] = 'CORRUPT';
    },
    for (final rate in ['0.02', '0.0120'])
      'A agreed but noncanonical rate $rate': (w) {
        w['snapshot']['card_charge_policy']['cards']['owner'][0]['parameters']
            ['rate'] = rate;
        w['state']['owner_discount_month']['projection_policy']['parameters']
            ['rate'] = rate;
      },
    'B confirmed source excluded from current entries': (w) {
      w['state']['entries'].add(Map<String, dynamic>.from(
          w['state']['confirmed_planned_entries'][0]));
    },
    'B close source existence': (w) {
      w['state']['month_close_status']['unconfirmed_recurring_items'] = [
        {'kind': 'fixed', 'id': 999999, 'title': 'Missing', 'amount_value': 0}
      ];
    },
    'B canonical payment group ID': (w) {
      (w['state']['card_payment_status']['rows'] as List)
          .singleWhere((r) => r['is_group'] == true)['id'] = -99999;
    },
    'C ledger discount override': (w) {
      w['state']['entries'][0]['discount_override'] = 1;
    },
    'C ledger date': (w) {
      w['state']['entries'][0]['entry_date'] = '2026-10-04';
    },
    'C confirmation metadata': (w) {
      w['state']['entries'][0]['confirmed_month'] = '2026-09';
    },
    'C panel semantics': (w) {
      w['state']['panels'][0]['due_day'] = 27;
    },
    'C cash income flag': (w) {
      final flow = w['state']['cash_flows'][0];
      flow['is_primary_income'] = 1 - flow['is_primary_income'];
    },
    'C close source amount': (w) {
      final source = (w['snapshot']['data']['monthly_panels'] as List)
          .firstWhere((r) => r['panel_type'] == 'fixed');
      w['state']['month_close_status']['unconfirmed_recurring_items'] = [
        {
          'kind': 'fixed',
          'id': source['id'],
          'title': source['title'],
          'amount_value': source['amount_value'] + 1
        }
      ];
    },
  };
  for (final attack in attacks.entries) {
    test(attack.key, () {
      expect(() => parseWire(corrupted(attack.value)), throwsFormatException);
    });
  }

  for (final field in ['payment part remaining', 'payment discount alias']) {
    test('same-root duplicated payment semantics $field', () {
      final wire = corrupted((w) {
        final row = (w['state']['card_payment_status']['rows'] as List)
            .firstWhere((row) => row['is_group'] == false);
        if (field == 'payment part remaining') {
          row['payment_parts'][0]['remaining_amount'] += 1;
        } else {
          row['discount_amount'] += 1;
        }
      });
      expect(() => parseWire(wire), throwsFormatException);
    });
  }

  for (final name in ['entries', 'panels', 'cash_flows']) {
    test('canonical SQL ordering $name', () {
      final wire = corrupted((w) {
        final rows = w['state'][name] as List;
        expect(rows.length, greaterThan(1));
        w['state'][name] = rows.reversed.toList();
      });
      expect(() => parseWire(wire), throwsFormatException);
    });
  }

  for (final field in [
    'title',
    'usage_place',
    'usage_item',
    'date_label',
    'group_label'
  ]) {
    test('explicit payment group presenter transform $field', () {
      final wire = corrupted((w) {
        final group = (w['state']['card_payment_status']['rows'] as List)
            .singleWhere((row) => row['is_group'] == true);
        group[field] = 'CONFLICT';
      });
      expect(() => parseWire(wire), throwsFormatException);
    });
  }

  // This matrix follows the wire-contract intersection, so a new duplicated
  // raw field cannot silently escape admission or this regression suite.
  for (final pair in [
    ('entries', 'LedgerEntry', 'Snapshot_ledger_entries'),
    ('confirmed_planned_entries', 'LedgerEntry', 'Snapshot_ledger_entries'),
    ('panels', 'MonthlyPanel', 'Snapshot_monthly_panels'),
    ('cash_flows', 'CashFlow', 'Snapshot_cash_flows'),
  ]) {
    final keys = bundleWireShapes[pair.$2]!
        .keys
        .where(bundleWireShapes[pair.$3]!.containsKey);
    for (final key in keys) {
      test('complete shared semantics ${pair.$1}.$key', () {
        final wire = corrupted((w) {
          final row = w['state'][pair.$1][0];
          final value = row[key];
          row[key] = value == null
              ? 1
              : value is num
                  ? value + 1
                  : value is bool
                      ? !value
                      : '${value}_CONFLICT';
        });
        expect(() => parseWire(wire), throwsFormatException);
      });
    }
    test('complete membership ${pair.$1}', () {
      final wire = corrupted((w) => w['state'][pair.$1].removeAt(0));
      expect(() => parseWire(wire), throwsFormatException);
    });
  }

  test('complete policy manifest, not only supported vocabulary', () {
    final valid = specimen()['snapshot']['card_charge_policy'] as Map;
    Iterable<List<Object>> leaves(Object? value, List<Object> path) sync* {
      if (value is Map) {
        for (final key in value.keys) {
          yield* leaves(value[key], [...path, key]);
        }
      } else if (value is List) {
        for (var i = 0; i < value.length; i++) {
          yield* leaves(value[i], [...path, i]);
        }
      } else {
        yield path;
      }
    }

    for (final path in leaves(valid, [])) {
      // covered_through is Snapshot data coverage, not a registered policy
      // definition. Its separate calendar/hash contract remains unchanged.
      if (path.first == 'covered_through') continue;
      final wire = corrupted((w) {
        dynamic parent = w['snapshot']['card_charge_policy'];
        for (final key in path.take(path.length - 1)) {
          parent = parent[key];
        }
        final key = path.last;
        final value = parent[key];
        parent[key] = value is int ? value + 1 : '${value}_CONFLICT';
      });
      expect(() => parseWire(wire), throwsFormatException,
          reason: path.join('.'));
    }
  });
}
