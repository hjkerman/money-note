// Admission-only identity checks. Never calculate discounts, eligibility,
// Summary or a replacement financial projection on the client.
import 'dart:convert';

import 'authoritative_bundle_contract.dart';
import 'authoritative_bundle_validation.dart';
import 'generated/bundle_policy_manifest.dart';
import 'money.dart';

void validateCanonicalBundlePolicy(Map policy) {
  final canonical = jsonDecode(canonicalBundlePolicyJson) as Map;
  for (final key in ['schema_version', 'classifier', 'profile_selectors']) {
    if (bundleCanonicalJson(policy[key]) !=
        bundleCanonicalJson(canonical[key])) {
      invalidBundle('noncanonical policy.$key');
    }
  }
  // Match backend manifest compatibility exactly: preserved binding prefix;
  // omitted later bindings must start AFTER the Snapshot's covered month.
  for (final scope in (canonical['cards'] as Map).keys) {
    final expected = canonical['cards'][scope] as List;
    final actual = policy['cards'][scope] as List;
    if (actual.isEmpty ||
        actual.length > expected.length ||
        bundleCanonicalJson(actual) !=
            bundleCanonicalJson(expected.take(actual.length).toList()) ||
        expected.skip(actual.length).any((binding) =>
            (binding['effective_from'] as String)
                .compareTo(policy['covered_through'] as String) <=
            0)) {
      invalidBundle('noncanonical policy binding.$scope');
    }
  }
}

// Compare the COMPLETE overlap of raw and typed wire contracts. A newly added
// duplicated field automatically participates, rather than requiring one more
// hand-picked if. Values are not repaired; integral REAL/int values compare as
// the backend model does. Exceptions below are explicit presenter transforms.
void validateSharedBundleEntity(
    Map projected, Map raw, String projection, String snapshot,
    {Map<String, Object?> overrides = const {}}) {
  for (final key in bundleWireShapes[projection]!.keys) {
    if (!bundleWireShapes[snapshot]!.containsKey(key)) {
      continue;
    }
    final expected = overrides.containsKey(key) ? overrides[key] : raw[key];
    if (projected[key] != expected) {
      invalidBundle('contradictory $projection.$key');
    }
  }
}

Map<int, Map<String, dynamic>> _rows(List rows) =>
    {for (final row in rows) row['id'] as int: row as Map<String, dynamic>};

void _membership(
    List projected, Iterable<Map<String, dynamic>> sources, String name,
    {required List<Object?> Function(Map) order, bool descending = false}) {
  final raw = {for (final row in sources) row['id']: row};
  final expected = raw.keys.toSet();
  final actual = projected.map((row) => row['id']).toSet();
  if (actual.length != expected.length || !actual.containsAll(expected)) {
    invalidBundle('noncanonical membership.$name');
  }
  // Check existing order; never sort/repair the received projection.
  for (var i = 1; i < projected.length; i++) {
    final before = order(raw[projected[i - 1]['id']]!);
    final after = order(raw[projected[i]['id']]!);
    if (_sqlOrder(before, after) * (descending ? -1 : 1) > 0) {
      invalidBundle('noncanonical ordering.$name');
    }
  }
}

int _sqlOrder(List<Object?> a, List<Object?> b) {
  for (var i = 0; i < a.length; i++) {
    final x = a[i], y = b[i];
    final compared = x == y
        ? 0
        : x == null
            ? -1
            : y == null
                ? 1
                : x is num && y is num
                    ? x.compareTo(y)
                    : (x as String).compareTo(y as String);
    if (compared != 0) return compared;
  }
  return 0;
}

void validateCanonicalBundleProjections(Map wire) {
  final state = wire['state'] as Map;
  final data = wire['snapshot']['data'] as Map;
  final month =
      (wire['authority']['evaluation_date'] as String).substring(0, 7);
  final entries = _rows(data['ledger_entries']);
  final panels = _rows(data['monthly_panels']);
  final flows = _rows(data['cash_flows']);
  bool confirmed(Map row) =>
      row['book_section'] == 'current' &&
      row['entry_kind'] == 'planned' &&
      row['confirmed_month'] == month;
  _membership(
      state['entries'],
      entries.values
          .where((row) => row['book_section'] == 'current' && !confirmed(row)),
      'entries',
      order: (r) => [
            r['entry_kind'] == 'planned' ? r['due_day'] ?? 99 : 0,
            r['entry_kind'] == 'planned' ? null : r['entry_date'],
            r['sort_order'],
            r['id']
          ]);
  _membership(state['confirmed_planned_entries'],
      entries.values.where(confirmed), 'confirmed_planned_entries',
      order: (r) => [r['due_day'] ?? 99, r['sort_order'], r['id']]);
  _membership(
      state['panels'],
      panels.values.where((row) =>
          row['month'] == month ||
          ['fixed', 'frozen', 'claim', 'family_card']
              .contains(row['panel_type'])),
      'panels',
      order: (r) => [
            r['panel_type'] == 'fixed' ? 0 : 1,
            r['spent_on'] == null ? 1 : 0,
            r['spent_on'],
            r['sort_order'],
            r['id']
          ]);
  final calendar = DateTime.parse('$month-01');
  final start = DateTime(calendar.year, calendar.month - 1, 1)
      .toIso8601String()
      .substring(0, 10);
  final end = DateTime(calendar.year, calendar.month + 1, 0)
      .toIso8601String()
      .substring(0, 10);
  _membership(
      state['cash_flows'],
      flows.values.where((row) =>
          (row['occurred_on'] as String).compareTo(start) >= 0 &&
          (row['occurred_on'] as String).compareTo(end) <= 0),
      'cash_flows',
      order: (r) => [r['occurred_on'], r['sort_order'], r['id']],
      descending: true);

  for (final row in state['entries']) {
    validateSharedBundleEntity(
        row, entries[row['id']]!, 'LedgerEntry', 'Snapshot_ledger_entries');
    for (final field in [
      'confirmed_amount_value',
      'confirmed_effective_discount_amount',
      'confirmed_effective_amount_value'
    ]) {
      if (row[field] != null) invalidBundle('unexpected confirmed projection');
    }
  }
  final visible = _rows(state['entries']);
  for (final row in state['confirmed_planned_entries']) {
    final source = entries[row['id']]!;
    final child = entries.values.singleWhere((e) =>
        e['source_planned_entry_id'] == source['id'] &&
        e['confirmed_month'] == source['confirmed_month'] &&
        e['confirmed_at'] == source['confirmed_at']);
    // Confirmed source's displayed date is the owned actual child's date,
    // including archive NULL dates. Every other shared source field is raw.
    validateSharedBundleEntity(
        row, source, 'LedgerEntry', 'Snapshot_ledger_entries',
        overrides: {'entry_date': child['entry_date']});
    final actual = visible[child['id']];
    if (actual != null) {
      for (final key in [
        'effective_discount_amount',
        'effective_amount_value'
      ]) {
        if (row['confirmed_$key'] != actual[key]) {
          invalidBundle('contradictory confirmed actual.$key');
        }
      }
    }
  }
  for (final row in state['panels']) {
    validateSharedBundleEntity(
        row, panels[row['id']]!, 'MonthlyPanel', 'Snapshot_monthly_panels');
  }
  for (final row in state['cash_flows']) {
    validateSharedBundleEntity(
        row, flows[row['id']]!, 'CashFlow', 'Snapshot_cash_flows');
  }

  final status = state['month_close_status'];
  for (final item in status['unconfirmed_recurring_items']) {
    final fixed = item['kind'] == 'fixed';
    final source = (fixed ? panels : entries)[item['id']];
    final target = status['oldest_open_month'];
    if (source == null ||
        target == null ||
        (fixed
            ? source['panel_type'] != 'fixed' ||
                (source['month'] as String).compareTo(target) > 0
            : source['entry_kind'] != 'planned' ||
                source['book_section'] != 'current') ||
        (source['confirmed_month'] == target &&
            source['confirmed_at'] != null &&
            (!fixed || source['confirmed_cash_flow_id'] != null))) {
      invalidBundle('noncanonical close source');
    }
    final expected = fixed
        ? {
            'kind': 'fixed',
            'id': source['id'],
            'title': source['title'],
            'amount_value': source['amount_value'] ?? 0,
          }
        : {
            'kind': 'planned',
            'id': source['id'],
            'title':
                (source['usage_place'] == null || source['usage_place'] == '')
                    ? source['title']
                    : source['usage_place'],
            'detail': source['usage_item'] ?? '',
            'amount_value': source['amount_value'] ?? 0,
            'due_day': source['due_day'],
          };
    if (bundleCanonicalJson(item) != bundleCanonicalJson(expected)) {
      invalidBundle('contradictory close source semantics');
    }
  }

  final active = (data['card_payment_batches'] as List)
      .where((batch) => batch['status'] == 'active')
      .toList();
  final batch = active.isEmpty ? null : active.single;
  final expectedMembers = <int>{};
  for (final item in data['card_payment_batch_items']) {
    final raw = entries[item['entry_id']]!;
    if (item['batch_id'] == batch?['id'] &&
        raw['entry_kind'] != 'planned' &&
        (raw['amount_value'] ?? 0) > 0) {
      expectedMembers.add(raw['id'] as int);
    }
  }
  final actualMembers = <int>{};
  for (final row in state['card_payment_status']['rows']) {
    final ids = (row['entry_ids'] as List).cast<int>();
    actualMembers.addAll(ids);
    final first = entries[ids.first]!;
    if (row['is_group'] == true) {
      if (ids.length < 2 ||
          row['id'] != -ids.first ||
          row['payment_key'] != 'group:toll:${ids.first}' ||
          row['is_toll'] != true) {
        invalidBundle('noncanonical payment group identity');
      }
      final principal = ids.fold<BigInt>(
          BigInt.zero,
          (total, id) =>
              total + BigInt.from(exactMoney(entries[id]!['amount_value'])));
      if (BigInt.from(exactMoney(row['amount_value'])) != principal ||
          BigInt.from(exactMoney(row['original_amount'])) != principal) {
        invalidBundle('contradictory grouped principal');
      }
      // These fields differ from raw ONLY by the explicit backend presenter
      // transform. Do not exclude them and accept arbitrary group semantics.
      validateSharedBundleEntity(
          row, first, 'PaymentRow', 'Snapshot_ledger_entries',
          overrides: {
            'id': -ids.first,
            'payment_key': 'group:toll:${ids.first}',
            'date_label': '',
            'group_label': '',
            'title': '하이패스/통행료 통합',
            'usage_place': '하이패스/통행료',
            'usage_item': '${ids.length}건',
            'amount_value': row['original_amount'],
          });
    } else {
      validateSharedBundleEntity(
          row, first, 'PaymentRow', 'Snapshot_ledger_entries');
      if (row['original_amount'] != first['amount_value']) {
        invalidBundle('contradictory payment principal');
      }
    }
    // These are duplicate server-computed values, NOT a recalculation of
    // discounts/payment burden. A group may contain unkeyed members, so its
    // parts are a complete alias only when every member has a stable key.
    if (row['discount_amount'] != row['effective_discount_amount']) {
      invalidBundle('contradictory payment discount alias');
    }
    if (ids.every((id) =>
        entries[id]!['payment_key'] != null &&
        entries[id]!['payment_key'] != '')) {
      final parts = (row['payment_parts'] as List).fold<BigInt>(
          BigInt.zero,
          (total, part) =>
              total + BigInt.from(exactMoney(part['remaining_amount'])));
      if (parts != BigInt.from(exactMoney(row['remaining_amount']))) {
        invalidBundle('contradictory payment remaining alias');
      }
    }
  }
  if (actualMembers.length != expectedMembers.length ||
      !actualMembers.containsAll(expectedMembers)) {
    invalidBundle('noncanonical payment membership');
  }
  final events = (data['card_payment_events'] as List)
      .where((event) => batch != null && event['batch_id'] == batch['id'])
      .cast<Map<String, dynamic>>();
  _membership(state['card_payment_status']['events'], events, 'payment events',
      order: (r) => [r['event_date'], r['id']], descending: true);
}
