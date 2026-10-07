// Read-only transport integrity/identity checks, never financial projections or
// historical repair. Server DB/API remain the financial authority.
import 'authoritative_bundle_contract.dart';
import 'authoritative_bundle_validation.dart';
import 'money.dart';

void validateAuthoritativeSnapshot(Map<String, dynamic> wire) {
  final s = wire['snapshot'] as Map<String, dynamic>;
  final data = s['data'] as Map<String, dynamic>;
  final manifest = s['manifest'] as Map<String, dynamic>;
  final policy = s['card_charge_policy'];
  for (final bindings in (policy['cards'] as Map).values) {
    if ((bindings as List).isEmpty) invalidBundle('empty policy history');
    for (final binding in bindings) {
      _policyParameters(binding);
    }
  }
  _policyParameters(
      policy['profile_selectors']['transit']['none_mode']['policy']);
  if (!validBundleTimestamp(s['exported_at'])) {
    invalidBundle('snapshot.exported_at');
  }
  for (final table in data.keys) {
    final rows = data[table] as List;
    final metadata = manifest['tables'][table] as Map<String, dynamic>;
    final columns = bundleWireShapes['Snapshot_$table']!.keys.toList()..sort();
    if (bundleCanonicalJson(metadata['columns']) !=
            bundleCanonicalJson(columns) ||
        metadata['row_count'] != rows.length ||
        metadata['sha256'] != bundleHash(rows)) {
      invalidBundle('snapshot.table.$table');
    }
  }
  final metadata = {
    for (final key in [
      'schema_version',
      'recurring_ownership_version',
      'exported_at',
      'range'
    ])
      key: s[key]
  };
  if (manifest['data_sha256'] != bundleHash(data) ||
      manifest['card_charge_policy_sha256'] !=
          bundleHash(s['card_charge_policy']) ||
      manifest['content_sha256'] !=
          bundleHash({
            ...metadata,
            'card_charge_policy': s['card_charge_policy'],
            'data': data
          }) ||
      s['snapshot_id'] != manifest['content_sha256']) {
    invalidBundle('snapshot.manifest');
  }
  final a = wire['authority'] as Map<String, dynamic>;
  if (a['state_revision'] < 0 ||
      a['state_fingerprint'] !=
          bundleHash({
            'schema_version': s['schema_version'],
            'range': s['range'],
            'card_charge_policy': s['card_charge_policy'],
            'data': data,
          })) {
    invalidBundle('authority');
  }
  final state = wire['state'] as Map<String, dynamic>;
  final day = a['evaluation_date'] as String;
  final month = day.substring(0, 7);
  final status = state['month_close_status'];
  if (wire['principal']['user_id'] <= 0 ||
      status['calendar_date'] != day ||
      status['calendar_month'] != month ||
      state['card_payment_status']['calendar_date'] != day) {
    invalidBundle('evaluation context');
  }
  for (final scope in ['owner', 'family']) {
    final policy = state['${scope}_discount_month'];
    if (policy['month'] != month ||
        policy['scope'] != scope ||
        !['enabled', 'disabled'].contains(policy['policy'])) {
      invalidBundle('policy context');
    }
    final descriptor = policy['projection_policy'];
    _policyParameters(descriptor);
  }
  if (state['transit_discount_profile']['card'] != 'transit' ||
      state['transit_discount_profile']['month'] != month ||
      !['none', 'owner']
          .contains(state['transit_discount_profile']['profile'])) {
    invalidBundle('transit context');
  }
  final settings = _indexed(data['app_settings'], 'key');
  for (final key in ['scheduled_income', 'cash_flow_balance', 'card_limit']) {
    if (!settings.containsKey(key) || !state['settings'].containsKey(key)) {
      invalidBundle('money setting.$key');
    }
  }
  if (bundleCanonicalJson(state['settings']) !=
      bundleCanonicalJson({
        for (final row in settings.values) row['key'] as String: row['value']
      })) {
    invalidBundle('settings view');
  }
  final lastClosed = settings['last_closed_month']?['value'];
  if (status['last_closed_month'] != lastClosed) invalidBundle('month status');
  _relationships(data, lastClosed as String?);
  _projectionIdentities(state, data, month);
}

// Validate policy descriptor structure only; never calculate a discount or
// classify an entry. Values/eligibility still come exclusively from the server.
void _policyParameters(Map definition) {
  if (definition['type'] == 'flat_statement') {
    final rate = definition['parameters']['rate'];
    if (rate is! String || !RegExp(r'^\d+(?:\.\d+)?$').hasMatch(rate)) {
      invalidBundle('policy rate');
    }
  }
}

Map<Object, Map<String, dynamic>> _indexed(List rows, [String key = 'id']) {
  final result = <Object, Map<String, dynamic>>{};
  for (final raw in rows) {
    final row = raw as Map<String, dynamic>;
    final id = row[key];
    if (id == null || result.containsKey(id)) {
      invalidBundle('duplicate/missing $key');
    }
    result[id] = row;
  }
  return result;
}

void _epoch(Map<String, dynamic> row) {
  final month = row['confirmed_month'];
  final stamp = row['confirmed_at'];
  if ((month == null) != (stamp == null)) {
    invalidBundle('partial recurring epoch');
  }
  if (month != null) {
    validateBundleShape(month, 'm', 'recurring month');
    if (!validBundleTimestamp(stamp)) invalidBundle('recurring timestamp');
  }
}

void _relationships(Map<String, dynamic> data, String? closed) {
  final entries = _indexed(data['ledger_entries']);
  final panels = _indexed(data['monthly_panels']);
  final flows = _indexed(data['cash_flows']);
  final batches = _indexed(data['card_payment_batches']);
  final events = _indexed(data['card_payment_events']);
  _indexed(data['card_payment_batch_items']);
  _indexed(data['card_payment_allocations']);
  _indexed(data['card_payment_deferrals'], 'entry_payment_key');
  _indexed(data['notification_candidate_registrations'], 'registration_key');
  _indexed(data['app_labels'], 'key');
  final keys = <Object, Map<String, dynamic>>{};
  final owned = <String, Map<String, dynamic>>{};
  String identity(Map<String, dynamic> row, Object sourceId) =>
      '$sourceId/${row['confirmed_month']}/${row['confirmed_at']}';
  for (final row in entries.values) {
    final key = row['payment_key'];
    if (key != null) {
      if (keys.containsKey(key)) {
        invalidBundle('duplicate payment key');
      }
      keys[key] = row;
    }
    final sourceId = row['source_planned_entry_id'];
    if (row['entry_kind'] == 'planned') {
      if (sourceId != null) {
        invalidBundle('recurring source');
      }
      _epoch(row);
      if (row['entry_date'] != null && row['confirmed_month'] == null) {
        invalidBundle('recurring source date');
      }
    } else if (sourceId != null ||
        (row['entry_kind'] == 'expense' &&
            (row['confirmed_month'] != null || row['confirmed_at'] != null))) {
      final source = entries[sourceId];
      _epoch(row);
      if (row['entry_kind'] != 'expense' ||
          source?['entry_kind'] != 'planned' ||
          row['confirmed_month'] == null ||
          row['amount_value'] == null ||
          exactMoney(row['amount_value']) < 0) {
        invalidBundle('recurring child');
      }
      final id = identity(row, sourceId!);
      if (owned.containsKey(id)) invalidBundle('duplicate recurring child');
      owned[id] = row;
      if ((row['confirmed_month'] as String).compareTo(closed ?? '0000-00') >
              0 &&
          (source!['confirmed_month'] != row['confirmed_month'] ||
              source['confirmed_at'] != row['confirmed_at'])) {
        invalidBundle('wrong active recurring epoch');
      }
    }
  }
  for (final source in entries.values.where((row) =>
      row['entry_kind'] == 'planned' && row['confirmed_month'] != null)) {
    if (!owned.containsKey(identity(source, source['id']))) {
      invalidBundle('missing recurring child');
    }
  }
  if (batches.values.where((row) => row['status'] == 'active').length > 1) {
    invalidBundle('multiple active batches');
  }
  final batchOwners = <Object, Object>{};
  final itemEntries = <Object>{};
  for (final item in data['card_payment_batch_items']) {
    final entry = entries[item['entry_id']];
    if (!batches.containsKey(item['batch_id']) ||
        entry == null ||
        entry['entry_kind'] == 'planned' ||
        item['entry_payment_key'] == '' ||
        entry['payment_key'] != item['entry_payment_key'] ||
        entry['amount_value'] == null ||
        exactMoney(entry['amount_value']) < 0 ||
        batchOwners.containsKey(item['entry_payment_key']) ||
        !itemEntries.add(item['entry_id'])) {
      invalidBundle('card batch ownership');
    }
    batchOwners[item['entry_payment_key']] = item['batch_id'];
  }
  final pairs = <String>{};
  final totals = <Object, int>{};
  for (final part in data['card_payment_allocations']) {
    final event = events[part['payment_event_id']];
    final entry = keys[part['entry_payment_key']];
    final amount = exactMoney(part['amount_value']);
    if (event == null ||
        entry == null ||
        entry['entry_kind'] == 'planned' ||
        amount < 0 ||
        !pairs
            .add('${part['payment_event_id']}/${part['entry_payment_key']}') ||
        (event['batch_id'] != null &&
            batchOwners[part['entry_payment_key']] != event['batch_id'])) {
      invalidBundle('payment allocation ownership');
    }
    final total = (totals[part['payment_event_id']] ?? 0) + amount;
    if (total > maxMoney) invalidBundle('payment allocation total');
    totals[part['payment_event_id']] = total;
  }
  final eventFlows = <Object>{};
  for (final event in events.values) {
    final flowId = event['cash_flow_id'];
    final total = exactMoney(event['total_amount']);
    if ((event['batch_id'] != null &&
            !batches.containsKey(event['batch_id'])) ||
        total != (totals[event['id']] ?? 0)) {
      invalidBundle('payment event');
    }
    if (flowId != null &&
        (!eventFlows.add(flowId) || !flows.containsKey(flowId))) {
      invalidBundle('payment cash ownership');
    }
    if (event['event_type'] == 'immediate' &&
        ((total > 0 && flowId == null) ||
            (flowId != null &&
                exactMoney(flows[flowId]!['amount_value']) != -total))) {
      invalidBundle('payment outflow');
    }
  }
  final fixedFlows = <Object>{};
  for (final panel in panels.values) {
    if (panel['panel_type'] != 'fixed' &&
        panel['confirmed_cash_flow_id'] == null) {
      continue;
    }
    final flowId = panel['confirmed_cash_flow_id'];
    if (flowId == null) {
      if (panel['confirmed_at'] != null || panel['confirmed_month'] != null) {
        invalidBundle('missing fixed relationship');
      }
      continue;
    }
    final flow = flows[flowId];
    if (panel['panel_type'] != 'fixed' ||
        flow == null ||
        !fixedFlows.add(flowId) ||
        eventFlows.contains(flowId) ||
        panel['spent_on'] != flow['occurred_on'] ||
        exactMoney(flow['amount_value']) > 0 ||
        flow['is_primary_income'] != 0 ||
        !validBundleTimestamp(panel['confirmed_at']) ||
        !_fixedPeriod(panel['spent_on'], panel['confirmed_month'], closed)) {
      invalidBundle('fixed relationship');
    }
  }
}

bool _fixedPeriod(String day, Object? month, String? closed) {
  if (month == day.substring(0, 7)) return true;
  final date = DateTime.parse(day);
  final next =
      DateTime(date.year, date.month + 1, 1).toIso8601String().substring(0, 7);
  return date.day == DateTime(date.year, date.month + 1, 0).day &&
      closed == day.substring(0, 7) &&
      month == next;
}

void _projectionIdentities(
    Map<String, dynamic> state, Map<String, dynamic> data, String month) {
  final entries = _indexed(data['ledger_entries']);
  final panels = _indexed(data['monthly_panels']);
  final flows = _indexed(data['cash_flows']);
  final events = _indexed(data['card_payment_events']);
  for (final row in [
    ...state['entries'],
    ...state['confirmed_planned_entries']
  ]) {
    final raw = entries[row['id']];
    if (raw == null ||
        row['book_section'] != raw['book_section'] ||
        row['entry_kind'] != raw['entry_kind'] ||
        row['payment_key'] != raw['payment_key'] ||
        row['amount_value'] != raw['amount_value']) {
      invalidBundle('entry projection identity');
    }
    if (row['amount_value'] != null && row['effective_amount_value'] == null) {
      invalidBundle('missing effective entry amount');
    }
  }
  for (final row in state['confirmed_planned_entries']) {
    final source = entries[row['id']]!;
    if (source['entry_kind'] != 'planned' ||
        source['confirmed_month'] != month) {
      invalidBundle('confirmed source context');
    }
    final children = entries.values
        .where((e) =>
            e['source_planned_entry_id'] == source['id'] &&
            e['confirmed_month'] == source['confirmed_month'] &&
            e['confirmed_at'] == source['confirmed_at'])
        .toList();
    if (children.length != 1 ||
        row['confirmed_amount_value'] != children.single['amount_value'] ||
        row['confirmed_effective_discount_amount'] == null ||
        row['confirmed_effective_amount_value'] == null) {
      invalidBundle('confirmed actual projection');
    }
  }
  for (final row in state['panels']) {
    final raw = panels[row['id']];
    if (raw == null ||
        row['panel_type'] != raw['panel_type'] ||
        row['confirmed_cash_flow_id'] != raw['confirmed_cash_flow_id'] ||
        row['amount_value'] != raw['amount_value']) {
      invalidBundle('panel projection identity');
    }
    if (row['amount_value'] != null && row['effective_amount_value'] == null) {
      invalidBundle('missing effective panel amount');
    }
    final flow = flows[row['confirmed_cash_flow_id']];
    if (flow != null &&
        row['confirmed_amount_value'] !=
            exactMoney(flow['amount_value']).abs()) {
      invalidBundle('fixed actual projection');
    }
  }
  for (final row in state['cash_flows']) {
    final raw = flows[row['id']];
    if (raw == null ||
        raw['amount_value'] != row['amount_value'] ||
        raw['occurred_on'] != row['occurred_on']) {
      invalidBundle('cash projection identity');
    }
  }
  for (final row in state['card_payment_status']['rows']) {
    final ids = row['entry_ids'] as List;
    if (ids.isEmpty ||
        ids.toSet().length != ids.length ||
        ids.any((id) => !entries.containsKey(id))) {
      invalidBundle('payment member identity');
    }
    final keyed = ids
        .map((id) => entries[id]!)
        .where((raw) => raw['payment_key'] != null && raw['payment_key'] != '')
        .toList();
    if (bundleCanonicalJson(row['payment_keys']) !=
            bundleCanonicalJson(
                keyed.map((raw) => raw['payment_key']).toList()) ||
        bundleCanonicalJson((row['payment_parts'] as List)
                .map((p) => p['entry_id'])
                .toList()) !=
            bundleCanonicalJson(keyed.map((raw) => raw['id']).toList()) ||
        (row['is_group'] == false &&
            (ids.length != 1 || ids.single != row['id']))) {
      invalidBundle('payment member lists');
    }
    for (final part in row['payment_parts']) {
      final raw = entries[part['entry_id']];
      if (raw == null ||
          raw['payment_key'] != part['entry_payment_key'] ||
          part['remaining_amount'] < 0) {
        invalidBundle('payment projection identity');
      }
    }
  }
  for (final event in state['card_payment_status']['events']) {
    if (bundleCanonicalJson(event) !=
        bundleCanonicalJson(events[event['id']])) {
      invalidBundle('payment event projection');
    }
  }
}
