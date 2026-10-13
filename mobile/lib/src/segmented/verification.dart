// T6.6C §§10/11/18/19/23. Structural facts only; never financial projections.
import 'dart:collection';
import 'dart:convert';
import 'dart:typed_data';

import '../authoritative_snapshot_validation.dart';
import 'c1.dart';
import 'graph.dart';
import 'object.dart';
import 'protocol.dart';
import 'work.dart';

part 'incremental_verification.dart';
part 'patricia_edit.dart';

typedef ObjectLoader = VerifiedObject Function(ObjectRef ref);

class RawChange {
  const RawChange(this.table, this.key, this.before, this.after);
  final String table;
  final List<dynamic> key;
  final Map<String, dynamic>? before, after;
}

class TreeDifference {
  const TreeDifference(this.changes, this.reusedSubtrees, this.examinedObjects,
      [this.targetLeaves = const {}]);
  final List<RawChange> changes;
  final int reusedSubtrees, examinedObjects;
  final Map<String, ObjectRef> targetLeaves;
}

// Ordered PK frontier. Leaf boundaries need not align. A row cursor is retained
// when only the other leaf ends, so split/merge/moved rows cannot become deletes.
TreeDifference diffRawTrees(
    SyncTarget? base, SyncTarget target, ObjectLoader load,
    {int maxChanges = 1000000}) {
  final changes = <RawChange>[];
  final targetLeaves = <String, ObjectRef>{};
  var reused = 0, examined = 0;
  Map<String, dynamic> read(ObjectRef ref) {
    examined++;
    return load(ref).body;
  }

  final oldRoot = base == null ? null : read(base.roots['raw']!);
  final newRoot = read(target.roots['raw']!);
  for (var t = 0; t < segmentedTables.length; t++) {
    final table = segmentedTables[t];
    final left = Queue<Map<String, dynamic>>(),
        right = Queue<Map<String, dynamic>>();
    if (oldRoot != null) {
      left.add(Map<String, dynamic>.from(oldRoot['tables'][t]['root']));
    }
    right.add(Map<String, dynamic>.from(newRoot['tables'][t]['root']));
    final a = Queue<Map<String, dynamic>>(), b = Queue<Map<String, dynamic>>();
    void expand(
        Queue<Map<String, dynamic>> frontier, Queue<Map<String, dynamic>> rows,
        {bool targetSide = false}) {
      final d = frontier.removeFirst();
      final body = read(ObjectRef.parse(d['ref']));
      if (body['kind'] == 'snapshot-leaf') {
        if (targetSide) {
          for (final row in body['rows']) {
            targetLeaves[_factId([table, row['key']])] =
                ObjectRef.parse(d['ref']);
          }
        }
        rows.addAll(
            (body['rows'] as List).map((r) => Map<String, dynamic>.from(r)));
      } else {
        for (final child in (body['children'] as List).reversed) {
          frontier.addFirst(Map<String, dynamic>.from(child));
        }
      }
    }

    while (
        left.isNotEmpty || right.isNotEmpty || a.isNotEmpty || b.isNotEmpty) {
      if (a.isEmpty &&
          b.isEmpty &&
          left.isNotEmpty &&
          right.isNotEmpty &&
          sameBytes(encodeC1(left.first), encodeC1(right.first))) {
        left.removeFirst();
        right.removeFirst();
        reused++;
        continue;
      }
      if (a.isEmpty && left.isNotEmpty) {
        expand(left, a);
        continue;
      }
      if (b.isEmpty && right.isNotEmpty) {
        expand(right, b, targetSide: true);
        continue;
      }
      if (a.isEmpty && b.isEmpty) continue;
      final comparison = a.isEmpty
          ? 1
          : b.isEmpty
              ? -1
              : TreeKey.parse(a.first['key'], table)
                  .compareTo(TreeKey.parse(b.first['key'], table));
      final old = comparison <= 0 ? a.removeFirst() : null;
      final next = comparison >= 0 ? b.removeFirst() : null;
      if (old != null &&
          next != null &&
          sameBytes(encodeC1(old['value']), encodeC1(next['value']))) {
        continue;
      }
      if (changes.length >= maxChanges) rejectSegment('DIFF_BUDGET');
      changes.add(RawChange(
          table,
          List.unmodifiable((old ?? next)!['key'] as List),
          old?['value'] as Map<String, dynamic>?,
          next?['value'] as Map<String, dynamic>?));
    }
  }
  return TreeDifference(List.unmodifiable(changes), reused, examined,
      Map.unmodifiable(targetLeaves));
}

String _factId(Object? key) => base64Encode(encodeC1(key));
List<dynamic> _key(Object? value) => [value is String ? 't' : 'i', '$value'];

const _references = <String, Map<String, String>>{
  'ledger_entries': {'source_planned_entry_id': 'ledger_entries'},
  'monthly_panels': {'confirmed_cash_flow_id': 'cash_flows'},
  'card_payment_events': {
    'batch_id': 'card_payment_batches',
    'cash_flow_id': 'cash_flows'
  },
  'card_payment_batch_items': {
    'batch_id': 'card_payment_batches',
    'entry_id': 'ledger_entries'
  },
  'card_payment_allocations': {
    'payment_event_id': 'card_payment_events',
    'entry_payment_key': '@ledger_payment_key'
  },
};

Map<String, Map<String, dynamic>> rowFacts(SyncTarget target, String table,
    List<dynamic> key, Map<String, dynamic> row) {
  final digest = objectHash(
      'row',
      encodeC1({
        'ns': target.ns.toJson(),
        'raw_schema': target.versions.rawSchema,
        'table': table,
        'key': key,
        'value': row
      }));
  final result = <String, Map<String, dynamic>>{};
  void add(List<dynamic> k, Object? value) =>
      result[_factId(k)] = {'key': k, 'value': value};
  void unique(String domain, List<dynamic> parts) =>
      add(['unique', domain, parts], [table, key]);
  add(['pk', table, key], digest);
  switch (table) {
    case 'ledger_entries':
      if (row['payment_key'] != null) {
        unique('ledger_payment_key', [row['payment_key']]);
      }
      if (row['entry_kind'] == 'expense' &&
          row['source_planned_entry_id'] != null) {
        unique('recurring_child', [
          _key(row['source_planned_entry_id']),
          row['confirmed_month'],
          row['confirmed_at']
        ]);
      }
      if (row['entry_kind'] == 'planned' ||
          row['source_planned_entry_id'] != null ||
          row['confirmed_month'] != null ||
          row['confirmed_at'] != null) {
        add(['context_reverse', 'last_closed_month', table, key], digest);
      }
    case 'monthly_panels':
      if (row['panel_type'] == 'fixed') {
        add(['context_reverse', 'last_closed_month', table, key], digest);
        if (row['confirmed_cash_flow_id'] != null) {
          unique('cash_owner', [_key(row['confirmed_cash_flow_id'])]);
        }
      }
    case 'card_payment_batch_items':
      unique('batch_pair', [_key(row['batch_id']), row['entry_payment_key']]);
      unique('batch_key', [row['entry_payment_key']]);
      unique('batch_entry', [_key(row['entry_id'])]);
    case 'card_payment_events':
      if (row['idempotency_key'] != null) {
        unique('event_idempotency', [row['idempotency_key']]);
      }
      if (row['cash_flow_id'] != null) {
        unique('cash_owner', [_key(row['cash_flow_id'])]);
      }
    case 'card_payment_allocations':
      final event = _key(row['payment_event_id']);
      unique('allocation_pair', [event, row['entry_payment_key']]);
      add(['allocation', event, row['entry_payment_key'], key],
          '${(row['amount_value'] as num).toInt()}');
  }
  for (final e in (_references[table] ?? {}).entries) {
    if (row[e.key] != null) {
      final destination = _key(row[e.key]);
      add(['ref', table, key, e.key], [e.value, destination]);
      add(['reverse', e.value, destination, table, key, e.key], digest);
    }
  }
  return result;
}

Map<String, Map<String, dynamic>> buildRawFacts(
    SyncTarget target, Map<String, dynamic> data) {
  final result = <String, Map<String, dynamic>>{};
  void add(Map<String, dynamic> fact) {
    if (result.containsKey(_factId(fact['key']))) {
      rejectSegment('FACT_DUPLICATE');
    }
    result[_factId(fact['key'])] = fact;
  }

  for (final table in segmentedTables) {
    for (final row in data[table] as List) {
      for (final fact
          in rowFacts(target, table, _key(row[primaryColumn(table)]), row)
              .values) {
        add(fact);
      }
    }
  }
  final totals = <Object, BigInt>{}, counts = <Object, BigInt>{};
  for (final row in data['card_payment_allocations']) {
    final id = row['payment_event_id'] as Object;
    totals[id] =
        (totals[id] ?? BigInt.zero) + BigInt.from(row['amount_value'] as num);
    counts[id] = (counts[id] ?? BigInt.zero) + BigInt.one;
  }
  for (final event in data['card_payment_events']) {
    final id = event['id'];
    add({
      'key': ['aggregate', 'event', _key(id)],
      'value': ['${counts[id] ?? BigInt.zero}', '${totals[id] ?? BigInt.zero}']
    });
  }
  add({
    'key': ['aggregate', 'active_batch'],
    'value':
        '${(data['card_payment_batches'] as List).where((r) => r['status'] == 'active').length}'
  });
  final closed = (data['app_settings'] as List)
      .where((r) => r['key'] == 'last_closed_month');
  add({
    'key': ['context', 'last_closed_month'],
    'value': closed.isEmpty ? null : closed.single['value']
  });
  return result;
}

// Independently construct canonical Patricia bytes/Refs from F(raw), including
// exact-key collision buckets. Downloaded index claims are never the oracle.
ObjectRef canonicalFactsRoot(
    SyncTarget target, Iterable<Map<String, dynamic>> facts) {
  final common = {
    'ns': target.ns.toJson(),
    'canon': 1,
    'structural': 1,
    'raw_schema': target.versions.rawSchema
  };
  ObjectRef make(String kind, Map<String, dynamic> fields) {
    final bytes = encodeC1({'kind': kind, ...common, ...fields});
    return ObjectRef.parse(
        {'hash': objectHash(kind, bytes), 'bytes': '${bytes.length}'});
  }

  final buckets = <String, List<Map<String, dynamic>>>{};
  for (final f in facts) {
    buckets
        .putIfAbsent(objectHash('fact-key', encodeC1(f['key'])), () => [])
        .add(f);
  }
  String bits(String h) => h
      .split('')
      .map((v) => int.parse(v, radix: 16).toRadixString(2).padLeft(4, '0'))
      .join();
  (ObjectRef, int) build(List<String> keys) {
    if (keys.isEmpty) return (make('index-empty', {'count': '0'}), 0);
    if (keys.length == 1) {
      final values = buckets[keys.single]!
        ..sort((a, b) => byteCompare(encodeC1(a['key']), encodeC1(b['key'])));
      return (
        make('index-leaf', {
          'digest': keys.single,
          'count': '${values.length}',
          'facts': values
        }),
        values.length
      );
    }
    final first = bits(keys.first), last = bits(keys.last);
    var n = 0;
    while (n < 256 && first[n] == last[n]) {
      n++;
    }
    final split = keys.indexWhere((k) => bits(k)[n] == '1');
    final left = build(keys.sublist(0, split)),
        right = build(keys.sublist(split));
    return (
      make('index-node', {
        'prefix': first.substring(0, n),
        'left': left.$1.toJson(),
        'right': right.$1.toJson(),
        'count': '${left.$2 + right.$2}'
      }),
      left.$2 + right.$2
    );
  }

  final node = build(buckets.keys.toList()..sort());
  return make('index-root', {'facts': node.$1.toJson(), 'count': '${node.$2}'});
}

class CompleteGenerationProof {
  CompleteGenerationProof._(this.manifest, this.graph, this.difference,
      this._receipt, this.verificationMicroseconds, this._catalog,
      [this._rowsDelta = const {}, this._factsDelta = const {}]);
  static const validator = 'segmented-e3/1';
  final ObservationManifest manifest;
  final GraphClosure graph;
  final TreeDifference difference;
  final Uint8List _receipt;
  Uint8List get receipt => Uint8List.fromList(_receipt);
  final int verificationMicroseconds;
  final _RawCatalog _catalog;
  final Map<String, Map<String, dynamic>?> _rowsDelta, _factsDelta;

  // Called only after accepted COMMIT/readback. Never grants publication authority.
  void adoptVerifiedData() => _catalog.adopt(this);
  bool get hasMatchingDataIdentity =>
      _catalog.syncRoot == manifest.target.syncRoot;

  // Versioned data association for additive root pins. Keep /1's complete
  // sorted-ref digest unchanged for existing durable receipts and the oracle.
  CompleteGenerationProof withRootAssociation() {
    final evidence = decodeC1(_receipt) as Map<String, dynamic>;
    return CompleteGenerationProof._(
        manifest,
        graph,
        difference,
        encodeC1({
          ...evidence,
          'validator': 'segmented-e3/2',
          'object_set': graphAssociation(
              manifest.target, graph.objects.length, graph.edges)
        }),
        verificationMicroseconds,
        _catalog,
        _rowsDelta,
        _factsDelta);
  }
}

String graphAssociation(SyncTarget target, int objects, int edges) =>
    localChecksum(encodeC1({
      'roots': {
        for (final role in ['raw', 'index', 'hot', 'control'])
          role: target.roots[role]!.toJson()
      },
      'objects': objects,
      'edges': edges
    }));

Future<CompleteGenerationProof> verifyCompleteGeneration(
    ObservationManifest manifest, ObjectLoader load,
    {ObservationManifest? base,
    int maxObjects = 100000,
    SegmentedWork? work}) async {
  work?.add('full_verifications');
  final timer = Stopwatch()..start();
  final target = manifest.target;
  if (base != null) {
    if (!sameBytes(
            encodeC1(base.target.ns.toJson()), encodeC1(target.ns.toJson())) ||
        base.target.principalId != target.principalId) {
      rejectSegment('BASE_CONTEXT_INVALID');
    }
    if (BigInt.parse(target.revision) < BigInt.parse(base.target.revision)) {
      rejectSegment('TARGET_STALE');
    }
    if (target.revision == base.target.revision &&
        (!target.roots['raw']!.matches(base.target.roots['raw']!) ||
            !target.roots['index']!.matches(base.target.roots['index']!))) {
      rejectSegment('REVISION_ROOT_CONFLICT');
    }
  }
  final graph = await verifyAcquisitionGraph(
      target, (edge, _) async => load(edge.ref),
      maxObjects: maxObjects, maxEdges: maxObjects * 4);
  final data = <String, dynamic>{
    for (final t in segmentedTables) t: <Map<String, dynamic>>[]
  };
  final locations = <String, ObjectRef>{};
  for (final ref in graph.objects) {
    final obj = load(ref);
    if (obj.kind == 'snapshot-leaf') {
      final b = obj.body;
      (data[b['table']] as List).addAll((b['rows'] as List)
          .map<Map<String, dynamic>>(
              (r) => Map<String, dynamic>.from(r['value'])));
      for (final row in b['rows']) {
        locations[_factId([b['table'], row['key']])] = ref;
      }
    }
  }
  final hot = load(target.roots['hot']!).body,
      control = load(target.roots['control']!).body;
  try {
    validateSegmentedRawProjection(
        data: data,
        state: hot['state'],
        policy: control['card_charge_policy'],
        evaluationDate: target.context.date);
  } on FormatException {
    rejectSegment('RAW_HOT_ASSOCIATION_INVALID');
  }
  final facts = buildRawFacts(target, data);
  work?.add('full_raw_rows',
      data.values.fold<int>(0, (n, rows) => n + (rows as List).length));
  work?.add('full_fact_rows', facts.length);
  work?.add('canonical_full_builds');
  if (!canonicalFactsRoot(target, facts.values)
      .matches(target.roots['index']!)) {
    rejectSegment('GLOBAL_INDEX_INVALID');
  }
  final difference = diffRawTrees(base?.target, target, load);
  if (base != null) {
    // Accepted base provenance is revalidated, never inferred from cache presence.
    final prior = await verifyCompleteGeneration(base, load,
        maxObjects: maxObjects, work: work);
    final oldData = <String, dynamic>{
      for (final t in segmentedTables) t: <Map<String, dynamic>>[]
    };
    for (final ref in prior.graph.objects) {
      final obj = load(ref);
      if (obj.kind == 'snapshot-leaf') {
        final b = obj.body;
        (oldData[b['table']] as List).addAll((b['rows'] as List)
            .map<Map<String, dynamic>>(
                (r) => Map<String, dynamic>.from(r['value'])));
      }
    }
    final transitioned = buildRawFacts(base.target, oldData);
    work?.add('full_fact_rows', transitioned.length);
    work?.add('canonical_full_builds');
    for (final change in difference.changes) {
      if (change.before != null) {
        for (final f
            in rowFacts(base.target, change.table, change.key, change.before!)
                .values) {
          final old = transitioned.remove(_factId(f['key']));
          if (old == null || !sameBytes(encodeC1(old), encodeC1(f))) {
            rejectSegment('DIFF_OLD_MEMBERSHIP_INVALID');
          }
        }
      }
    }
    for (final change in difference.changes) {
      if (change.after != null) {
        for (final f
            in rowFacts(target, change.table, change.key, change.after!)
                .values) {
          if (transitioned.containsKey(_factId(f['key']))) {
            rejectSegment('DIFF_UNIQUE_CONFLICT');
          }
          transitioned[_factId(f['key'])] = f;
        }
      }
    }
    transitioned.removeWhere(
        (_, f) => ['aggregate', 'context'].contains((f['key'] as List).first));
    for (final f in facts.values) {
      if (['aggregate', 'context'].contains((f['key'] as List).first)) {
        transitioned[_factId(f['key'])] = f;
      }
    }
    if (!canonicalFactsRoot(target, transitioned.values)
        .matches(target.roots['index']!)) {
      rejectSegment('DIFF_INDEX_INVALID');
    }
  }
  final identities = graph.objects.map((r) => r.toJson()).toList()
    ..sort((a, b) => (a['hash'] as String).compareTo(b['hash'] as String));
  final receipt = encodeC1({
    'validator': CompleteGenerationProof.validator,
    'target': target.toJson(),
    'base_sync_root': base?.target.syncRoot,
    'objects': graph.objects.length,
    'object_set': localChecksum(encodeC1(identities)),
    'edges': graph.edges,
    'facts': '${facts.length}',
    'changed_rows': difference.changes.length,
    'reused_subtrees': difference.reusedSubtrees
  });
  return CompleteGenerationProof._(
      manifest,
      graph,
      difference,
      receipt,
      timer.elapsedMicroseconds,
      _RawCatalog(target.syncRoot, data, facts, locations));
}
