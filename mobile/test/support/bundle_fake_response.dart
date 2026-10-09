// Complete synthetic server response for existing state-machine test doubles.
// Never used by the application; no financial algorithm or parser fallback.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:money_note_mobile/src/authoritative_bundle_contract.dart';
import 'package:money_note_mobile/src/coherent_refresh_models.dart';

import '../authoritative_bundle_test.dart' show baseline, reseal;

Uint8List fakeBundleBytes(CoherentRefreshBundle acquired, {int principal = 1}) {
  final wire = jsonDecode(File('test/fixtures/authoritative_bundle_empty.json')
      .readAsStringSync()) as Map<String, dynamic>;
  final c = acquired.candidate;
  final b = baseline(acquired).toJson();
  final state = wire['state'];
  final data = wire['snapshot']['data'];
  final day = acquired.envelope.evaluationDate;
  final month = day.substring(0, 7);
  wire['principal']['user_id'] = principal;
  wire['authority']['evaluation_date'] = day;
  wire['authority']['state_revision'] = acquired.envelope.revision;
  wire['authority']['discount_policy_defaults'] =
      acquired.envelope.discountPolicyDefaults;
  for (final section in [
    'summary',
    'month_close_status',
    'card_payment_status',
    'owner_discount_month',
    'family_discount_month',
    'transit_discount_profile',
    'settings'
  ]) {
    state[section].addAll(b[section]);
  }
  state['summary']['current_month_spendable'] =
      c.summary.currentMonthSpendable ?? c.summary.remainingLiquidity;
  state['card_payment_status']['calendar_date'] = day;
  for (final section in ['budget', 'credit', 'payment']) {
    state['judgment'][section].addAll(b['judgment'][section]);
  }
  for (final section in [
    'entries',
    'confirmed_planned_entries',
    'panels',
    'cash_flows'
  ]) {
    final shape = section == 'panels'
        ? 'MonthlyPanel'
        : section == 'cash_flows'
            ? 'CashFlow'
            : 'LedgerEntry';
    state[section] = [
      for (final row in b[section])
        {
          for (final field in bundleWireShapes[shape]!.entries)
            field.key: row.containsKey(field.key)
                ? row[field.key]
                : field.value.startsWith('?')
                    ? null
                    : field.value == 'b'
                        ? false
                        : field.value == 'i' || field.value == 'n'
                            ? 0
                            : '',
        }
    ];
  }
  for (final panel in state['panels']) {
    panel['can_confirm_fixed'] ??= panel['panel_type'] == 'fixed';
    if (panel['panel_type'] == 'fixed') {
      panel['fixed_execution_month'] ??= month;
    }
  }
  // Old minimal model doubles omit the server's explicit no-discount amounts.
  for (final section in ['entries', 'panels']) {
    for (final row in state[section]) {
      row['effective_amount_value'] ??= row['amount_value'];
    }
  }
  for (final item in state['month_close_status']
      ['unconfirmed_recurring_items']) {
    if (item['kind'] == 'fixed') {
      item.remove('detail');
      item.remove('due_day');
    }
  }
  for (final (section, table) in [
    ('entries', 'ledger_entries'),
    ('panels', 'monthly_panels'),
    ('cash_flows', 'cash_flows')
  ]) {
    data[table] = [
      for (final row in state[section])
        {
          for (final field in bundleWireShapes['Snapshot_$table']!.entries)
            field.key: row.containsKey(field.key)
                ? row[field.key]
                : field.key == 'created_at' || field.key == 'updated_at'
                    ? '$day 12:00:00'
                    : null,
        }
    ];
  }
  data['app_settings'] = [
    for (final entry in (state['settings'] as Map).entries)
      {'key': entry.key, 'value': entry.value, 'updated_at': '$day 12:00:00'}
  ];
  // Reconciliation fixtures explicitly change the raw authority as well as
  // derived values. Never fabricate an arbitrary fingerprint that skips B-2.
  if (acquired.envelope.revision > 1) {
    data['app_labels'].add({
      'key': 'test-revision',
      'value': acquired.envelope.revision.toString(),
      'updated_at': '$day 12:00:00'
    });
  }
  state['owner_discount_month']['month'] = month;
  state['family_discount_month']['month'] = month;
  state['transit_discount_profile']['month'] = month;
  reseal(wire);
  return Uint8List.fromList(utf8.encode(jsonEncode(wire)));
}
