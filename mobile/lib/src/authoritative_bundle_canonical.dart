// Snapshot compatibility and raw-identity admission, NOT a financial oracle.
// Projection membership, eligibility, grouping and money calculations belong
// to the trusted server. See docs/architecture.md's trust-boundary contract.
import 'dart:convert';

import 'authoritative_bundle_contract.dart';
import 'authoritative_bundle_validation.dart';
import 'generated/bundle_policy_manifest.dart';

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

// Caller has already checked primary identities and raw references. Compare
// only the entities PRESENT in the response, not a recreated server selection.
void validateBundleProjectionStructure(
  Map state, {
  required Map<Object, Map<String, dynamic>> entries,
  required Map<Object, Map<String, dynamic>> panels,
  required Map<Object, Map<String, dynamic>> flows,
  required Map<Object, Map<String, dynamic>> confirmedActuals,
}) {
  for (final row in state['entries']) {
    validateSharedBundleEntity(
        row, entries[row['id']]!, 'LedgerEntry', 'Snapshot_ledger_entries');
  }
  final visible = {for (final row in state['entries']) row['id']: row};
  for (final row in state['confirmed_planned_entries']) {
    final source = entries[row['id']]!;
    final child = confirmedActuals[row['id']]!;
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
    if (source == null ||
        (fixed
            ? source['panel_type'] != 'fixed'
            : source['entry_kind'] != 'planned')) {
      invalidBundle('close source identity');
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

  for (final row in state['card_payment_status']['rows']) {
    final ids = (row['entry_ids'] as List).cast<int>();
    final first = entries[ids.first]!;
    if (row['is_group'] == true) {
      if (ids.length < 2 ||
          row['id'] != -ids.first ||
          row['payment_key'] != 'group:toll:${ids.first}' ||
          row['is_toll'] != true) {
        invalidBundle('noncanonical payment group identity');
      }
      // A composite is not the first member's raw entity. The server owns
      // its aggregate money, classifier/partition, order and presentation.
      // Its two explicit principal aliases must still agree. This does not
      // prove the aggregate by summing members or executing financial rules.
      if (row['amount_value'] != row['original_amount']) {
        invalidBundle('contradictory grouped principal alias');
      }
    } else {
      validateSharedBundleEntity(
          row, first, 'PaymentRow', 'Snapshot_ledger_entries');
      if (row['original_amount'] != first['amount_value']) {
        invalidBundle('contradictory payment principal');
      }
    }
    // Same-entity aliases may be compared, but no group financial sum is
    // independently recalculated. Agreement is NOT canonical money proof.
    if (row['discount_amount'] != row['effective_discount_amount']) {
      invalidBundle('contradictory payment discount alias');
    }
    final parts = row['payment_parts'] as List;
    if (row['is_group'] == false && parts.length == 1) {
      if (parts.single['remaining_amount'] != row['remaining_amount']) {
        invalidBundle('contradictory payment remaining alias');
      }
    }
  }
}
