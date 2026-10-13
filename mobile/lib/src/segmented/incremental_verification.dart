part of 'verification.dart';

// In-memory DATA provenance derived only from a complete verified accepted
// generation. Not persisted authority, not a replacement for AppState's guards.
class _RawCatalog {
  _RawCatalog(
      this.syncRoot, Map<String, dynamic> data, this.facts, this.locations) {
    for (final table in segmentedTables) {
      byTable[table] = <String>{};
      for (final row in data[table]) {
        final id = _factId([table, _key(row[primaryColumn(table)])]);
        rows[id] = row;
        byTable[table]!.add(id);
      }
    }
    for (final fact in facts.values) {
      _index(fact, true);
    }
  }
  String syncRoot;
  final Map<String, Map<String, dynamic>> rows = {}, facts;
  final Map<String, ObjectRef> locations;
  final Map<String, Set<String>> byTable = {}, incoming = {}, contexts = {};
  void _index(Map<String, dynamic> fact, bool add) {
    final key = fact['key'] as List, id = _factId(key);
    final target = key.first == 'reverse'
        ? _factId([key[1], key[2]])
        : key.first == 'context_reverse'
            ? key[1] as String
            : null;
    if (target == null) return;
    final index = key.first == 'reverse' ? incoming : contexts;
    if (add) {
      index.putIfAbsent(target, () => {}).add(id);
    } else {
      index[target]?.remove(id);
      if (index[target]?.isEmpty ?? false) index.remove(target);
    }
  }

  void adopt(CompleteGenerationProof proof) {
    if (identical(proof._catalog, this) &&
        syncRoot == proof.manifest.target.syncRoot) {
      return;
    }
    final expected = (decodeC1(proof.receipt) as Map)['base_sync_root'];
    if (syncRoot != expected) rejectSegment('BASE_PROVENANCE_STALE');
    for (final e in proof._factsDelta.entries) {
      final old = facts.remove(e.key);
      if (old != null) _index(old, false);
      if (e.value != null) {
        facts[e.key] = e.value!;
        _index(e.value!, true);
      }
    }
    locations.addAll(proof.difference.targetLeaves);
    for (final e in proof._rowsDelta.entries) {
      final table = (decodeC1(base64Decode(e.key)) as List).first as String;
      if (e.value == null) {
        rows.remove(e.key);
        locations.remove(e.key);
        byTable[table]!.remove(e.key);
      } else {
        rows[e.key] = e.value!;
        byTable[table]!.add(e.key);
      }
    }
    syncRoot = proof.manifest.target.syncRoot;
  }
}

const _relationFields = <String, List<String>>{
  'ledger_entries': [
    'payment_key',
    'entry_kind',
    'source_planned_entry_id',
    'confirmed_month',
    'confirmed_at',
    'entry_date',
    'amount_value'
  ],
  'cash_flows': ['amount_value', 'occurred_on', 'is_primary_income'],
  'monthly_panels': [
    'panel_type',
    'confirmed_cash_flow_id',
    'confirmed_month',
    'confirmed_at',
    'spent_on'
  ],
  'card_payment_batches': ['status'],
  'card_payment_batch_items': ['batch_id', 'entry_id', 'entry_payment_key'],
  'card_payment_events': [
    'batch_id',
    'cash_flow_id',
    'event_type',
    'total_amount',
    'idempotency_key'
  ],
  'card_payment_allocations': [
    'payment_event_id',
    'entry_payment_key',
    'amount_value'
  ]
};

Future<CompleteGenerationProof> verifyIncrementalGeneration(
    ObservationManifest manifest,
    CompleteGenerationProof base,
    ObjectLoader load,
    {int maxObjects = 100000,
    SegmentedWork? work}) async {
  final timer = Stopwatch()..start(),
      target = manifest.target,
      prior = base.manifest.target;
  if (!base.hasMatchingDataIdentity ||
      !prior.ns.matches(target.ns) ||
      prior.principalId != target.principalId ||
      !sameBytes(encodeC1(prior.versions.toJson()),
          encodeC1(target.versions.toJson()))) {
    rejectSegment('BASE_PROVENANCE_INVALID');
  }
  if (BigInt.parse(target.revision) < BigInt.parse(prior.revision)) {
    rejectSegment('TARGET_STALE');
  }
  if (target.revision == prior.revision &&
      (!target.roots['raw']!.matches(prior.roots['raw']!) ||
          !target.roots['index']!.matches(prior.roots['index']!))) {
    rejectSegment('REVISION_ROOT_CONFLICT');
  }
  final objects = <String, VerifiedObject>{};
  VerifiedObject read(ObjectRef ref) =>
      objects.putIfAbsent(ref.hash, () => load(ref));
  final graph = await verifyAcquisitionGraph(
      target, (e, _) async => read(e.ref),
      maxObjects: maxObjects,
      maxEdges: maxObjects * 4,
      reuse: base.graph.provenance,
      work: work);
  if (!base.hasMatchingDataIdentity) rejectSegment('BASE_PROVENANCE_STALE');
  final catalog = base._catalog, difference = diffRawTrees(prior, target, read);
  work?.add('tree_nodes_examined', difference.examinedObjects);
  work?.add('incremental_rows', difference.changes.length);
  final rows = <String, Map<String, dynamic>?>{},
      delta = <String, Map<String, dynamic>?>{};
  var factCount = catalog.facts.length;
  Map<String, dynamic>? fact(Object? key) {
    work?.add('index_fact_lookups');
    final id = _factId(key);
    return delta.containsKey(id) ? delta[id] : catalog.facts[id];
  }

  void remove(Map<String, dynamic> expected) {
    final old = fact(expected['key']);
    if (old == null || !sameBytes(encodeC1(old), encodeC1(expected))) {
      rejectSegment('DIFF_OLD_MEMBERSHIP_INVALID');
    }
    delta[_factId(expected['key'])] = null;
    factCount--;
  }

  void put(Map<String, dynamic> fresh) {
    if (fact(fresh['key']) != null) rejectSegment('DIFF_UNIQUE_CONFLICT');
    delta[_factId(fresh['key'])] = fresh;
    factCount++;
  }

  for (final change in difference.changes) {
    final id = _factId([change.table, change.key]);
    if (!sameBytes(encodeC1(catalog.rows[id]), encodeC1(change.before))) {
      rejectSegment('DIFF_OLD_MEMBERSHIP_INVALID');
    }
    // Seal private data separately from the public diff's caller-visible maps.
    rows[id] = change.after == null
        ? null
        : decodeC1(encodeC1(change.after)) as Map<String, dynamic>;
    if (change.before != null) {
      for (final f
          in rowFacts(prior, change.table, change.key, change.before!).values) {
        remove(f);
      }
    }
  }
  for (final change in difference.changes) {
    if (change.after != null) {
      for (final f in rowFacts(target, change.table, change.key,
              rows[_factId([change.table, change.key])]!)
          .values) {
        put(f);
      }
    }
  }
  Map<String, dynamic>? rowAt(String table, List<dynamic> key) {
    final id = _factId([table, key]);
    return rows.containsKey(id) ? rows[id] : catalog.rows[id];
  }

  Map<String, dynamic>? checked(String table, List<dynamic> key) {
    final id = _factId([table, key]), expected = rowAt(table, key);
    if (expected == null) return null;
    final location = difference.targetLeaves[id] ?? catalog.locations[id];
    if (location == null) rejectSegment('RAW_MEMBERSHIP_INVALID');
    final leaf = read(location).body;
    final found = (leaf['rows'] as List)
        .where((r) => sameBytes(encodeC1(r['key']), encodeC1(key)))
        .firstOrNull;
    if (leaf['table'] != table ||
        found == null ||
        !sameBytes(encodeC1(found['value']), encodeC1(expected))) {
      rejectSegment('RAW_MEMBERSHIP_INVALID');
    }
    work?.add('raw_entries_read');
    return expected;
  }

  final eventDeltas = <String, (BigInt, BigInt)>{};
  void eventDelta(Object id, int count, Object? amount) {
    final k = _factId(_key(id)),
        old = eventDeltas[k] ?? (BigInt.zero, BigInt.zero);
    eventDeltas[k] = (
      old.$1 + BigInt.from(count),
      old.$2 + BigInt.from(amount as num) * BigInt.from(count)
    );
  }

  var active = BigInt.parse(fact(['aggregate', 'active_batch'])!['value']);
  for (final c in difference.changes) {
    if (c.table == 'card_payment_allocations') {
      if (c.before != null) {
        eventDelta(
            c.before!['payment_event_id'], -1, c.before!['amount_value']);
      }
      if (c.after != null) {
        eventDelta(c.after!['payment_event_id'], 1, c.after!['amount_value']);
      }
    }
    if (c.table == 'card_payment_events') {
      eventDeltas.putIfAbsent(_factId(c.key), () => (BigInt.zero, BigInt.zero));
    }
    if (c.table == 'card_payment_batches') {
      if (c.before?['status'] == 'active') active -= BigInt.one;
      if (c.after?['status'] == 'active') active += BigInt.one;
    }
  }
  void replaceFact(Object key, Object? value, {bool absent = false}) {
    final old = fact(key),
        fresh = <String, dynamic>{'key': key, 'value': value};
    if (!absent && old != null && sameBytes(encodeC1(old), encodeC1(fresh))) {
      return;
    }
    if (old != null) remove(old);
    if (!absent) put(fresh);
  }

  for (final e in eventDeltas.entries) {
    final key = decodeC1(base64Decode(e.key)) as List<dynamic>,
        k = ['aggregate', 'event', key];
    final old = fact(k)?['value'] as List?;
    final count = BigInt.parse(old?[0] ?? '0') + e.value.$1,
        total = BigInt.parse(old?[1] ?? '0') + e.value.$2;
    final event = rowAt('card_payment_events', key);
    if (count < BigInt.zero ||
        total < BigInt.zero ||
        (event == null && (count != BigInt.zero || total != BigInt.zero)) ||
        (event != null && total != BigInt.from(event['total_amount'] as num))) {
      rejectSegment('RAW_RELATION_INVALID');
    }
    replaceFact(k, ['$count', '$total'], absent: event == null);
  }
  if (active < BigInt.zero || active > BigInt.one) {
    rejectSegment('RAW_RELATION_INVALID');
  }
  replaceFact(['aggregate', 'active_batch'], '$active');
  final settingIds = <String>{
    ...catalog.byTable['app_settings']!,
    ...rows.keys.where(
        (id) => (decodeC1(base64Decode(id)) as List).first == 'app_settings')
  };
  final settings = [
    for (final id in settingIds)
      if ((rows.containsKey(id) ? rows[id] : catalog.rows[id]) != null)
        (rows.containsKey(id) ? rows[id] : catalog.rows[id])!
  ];
  final closed = settings
      .where((r) => r['key'] == 'last_closed_month')
      .firstOrNull?['value'];
  final priorClosed =
      catalog.facts[_factId(['context', 'last_closed_month'])]!['value'];
  replaceFact(['context', 'last_closed_month'], closed);
  final editor = _PatriciaEdit(target, read, prior.roots['index']!, work);
  final removals = <Map<String, dynamic>>[],
      additions = <Map<String, dynamic>>[];
  for (final e in delta.entries) {
    final old = catalog.facts[e.key];
    if (old != null) removals.add(old);
    if (e.value != null) additions.add(e.value!);
  }
  int order(Map<String, dynamic> a, Map<String, dynamic> b) =>
      byteCompare(encodeC1(a['key']), encodeC1(b['key']));
  removals.sort(order);
  additions.sort(order);
  for (final f in removals) {
    editor.remove(f);
  }
  for (final f in additions) {
    editor.put(f);
  }
  if (!editor.finish().matches(target.roots['index']!)) {
    rejectSegment('GLOBAL_INDEX_INVALID');
  }
  work?.add('incremental_fact_changes', removals.length + additions.length);

  // Reverse index is accepted structural DATA, not a server hint. Only affected
  // relation fields start closure; unchanged financial components stay certified.
  final incomingNew = <String, Set<String>>{};
  for (final f in additions) {
    final k = f['key'] as List;
    if (k.first == 'reverse') {
      incomingNew.putIfAbsent(_factId([k[1], k[2]]), () => {}).add(_factId(k));
    }
  }
  final pending = Queue<String>(), seen = <String>{};
  void enqueue(String table, List<dynamic> key) =>
      pending.add(_factId([table, key]));
  for (final c in difference.changes) {
    final fields = _relationFields[c.table];
    if (fields != null &&
        (c.before == null ||
            c.after == null ||
            fields.any((f) => c.before![f] != c.after![f]))) {
      enqueue(c.table, c.key);
      if (c.table == 'ledger_entries') {
        for (final value in [
          c.before?['payment_key'],
          c.after?['payment_key']
        ]) {
          if (value != null) enqueue('@ledger_payment_key', _key(value));
        }
      }
    }
  }
  if (closed != priorClosed) {
    for (final id in {
      ...?catalog.contexts['last_closed_month'],
      ...additions
          .where((f) => (f['key'] as List).first == 'context_reverse')
          .map((f) => _factId(f['key']))
    }) {
      final f = delta.containsKey(id) ? delta[id] : catalog.facts[id];
      if (f != null) {
        final k = f['key'] as List;
        enqueue(k[2], k[3]);
      }
    }
  }
  final relationData = <String, dynamic>{
    for (final t in segmentedTables) t: <Map<String, dynamic>>[]
  };
  relationData['app_settings'] = settings;
  while (pending.isNotEmpty) {
    final id = pending.removeFirst();
    if (!seen.add(id)) continue;
    if (seen.length > 1000000) rejectSegment('RELATION_CLOSURE_BUDGET');
    final identity = decodeC1(base64Decode(id)) as List,
        table = identity[0] as String,
        key = identity[1] as List<dynamic>;
    for (final source in {...?catalog.incoming[id], ...?incomingNew[id]}) {
      final f =
          delta.containsKey(source) ? delta[source] : catalog.facts[source];
      if (f != null) {
        final k = f['key'] as List;
        enqueue(k[3], k[4]);
      }
    }
    if (table == '@ledger_payment_key') {
      final owner = fact([
        'unique',
        'ledger_payment_key',
        [key[1]]
      ])?['value'] as List?;
      if (owner != null) enqueue(owner[0], owner[1]);
      continue;
    }
    final row = checked(table, key);
    if (row == null) continue;
    work?.add('relation_rows');
    if (table != 'app_settings') (relationData[table] as List).add(row);
    if (table == 'ledger_entries' && row['payment_key'] != null) {
      enqueue('@ledger_payment_key', _key(row['payment_key']));
    }
    for (final e in (_references[table] ?? {}).entries) {
      if (row[e.key] != null) enqueue(e.value, _key(row[e.key]));
    }
  }
  try {
    validateSegmentedRelations(relationData, closed as String?);
  } on FormatException {
    rejectSegment('RAW_RELATION_INVALID');
  }

  final hot = read(target.roots['hot']!).body,
      control = read(target.roots['control']!).body;
  final state = hot['state'] as Map<String, dynamic>,
      hotRows = <String, Map<String, dynamic>>{};
  void hotRow(String table, Object id) {
    final key = _key(id), identity = _factId([table, key]);
    if (hotRows.containsKey(identity)) return;
    final row = checked(table, key);
    if (row == null) rejectSegment('RAW_HOT_ASSOCIATION_INVALID');
    hotRows[identity] = row;
    work?.add('hot_raw_rows');
  }

  for (final row in [
    ...state['entries'],
    ...state['confirmed_planned_entries']
  ]) {
    hotRow('ledger_entries', row['id']);
  }
  for (final row in state['confirmed_planned_entries']) {
    final source = rowAt('ledger_entries', _key(row['id']))!;
    final owner = fact([
      'unique',
      'recurring_child',
      [_key(row['id']), source['confirmed_month'], source['confirmed_at']]
    ])?['value'] as List?;
    if (owner != null) hotRow(owner[0], int.parse(owner[1][1]));
  }
  for (final row in state['panels']) {
    hotRow('monthly_panels', row['id']);
    final raw = rowAt('monthly_panels', _key(row['id']))!;
    if (raw['confirmed_cash_flow_id'] != null) {
      hotRow('cash_flows', raw['confirmed_cash_flow_id']);
    }
  }
  for (final row in state['cash_flows']) {
    hotRow('cash_flows', row['id']);
  }
  for (final row in state['card_payment_status']['rows']) {
    for (final id in row['entry_ids']) {
      hotRow('ledger_entries', id);
    }
  }
  for (final event in state['card_payment_status']['events']) {
    hotRow('card_payment_events', event['id']);
  }
  final hotData = <String, dynamic>{
    for (final t in segmentedTables) t: <Map<String, dynamic>>[]
  };
  for (final e in hotRows.entries) {
    final table = (decodeC1(base64Decode(e.key)) as List).first;
    (hotData[table] as List).add(e.value);
  }
  hotData['app_settings'] = settings;
  try {
    validateSegmentedHotProjection(
        data: hotData,
        state: state,
        policy: control['card_charge_policy'],
        evaluationDate: target.context.date);
  } on FormatException {
    rejectSegment('RAW_HOT_ASSOCIATION_INVALID');
  }
  // Version 2 evidence has a separate association from legacy /1 receipts.
  // Root-pin preparation additionally requires owning-store verified binding.
  final receipt = encodeC1({
    'validator': 'segmented-e3/2',
    'target': target.toJson(),
    'base_sync_root': prior.syncRoot,
    'objects': graph.objects.length,
    'object_set': graphAssociation(target, graph.objects.length, graph.edges),
    'edges': graph.edges,
    'facts': '$factCount',
    'changed_rows': difference.changes.length,
    'reused_subtrees': difference.reusedSubtrees
  });
  return CompleteGenerationProof._(
      manifest,
      graph,
      difference,
      receipt,
      timer.elapsedMicroseconds,
      catalog,
      Map.unmodifiable(rows),
      Map.unmodifiable(delta));
}
