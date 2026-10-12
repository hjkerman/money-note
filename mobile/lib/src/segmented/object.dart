import 'dart:typed_data';

import '../authoritative_bundle_contract.dart';
import '../authoritative_bundle_validation.dart';
import 'c1.dart';
import 'protocol.dart';

const segmentedTables = [
  'ledger_entries',
  'monthly_panels',
  'cash_flows',
  'card_payment_batches',
  'card_payment_batch_items',
  'card_payment_events',
  'card_payment_allocations',
  'card_payment_deferrals',
  'notification_candidate_registrations',
  'app_settings',
  'app_labels'
];
const transferableKinds = {
  'raw-root',
  'snapshot-leaf',
  'snapshot-node',
  'index-root',
  'index-empty',
  'index-leaf',
  'index-node',
  'hot',
  'control'
};

// Validation-only equivalent of backend isolated_sync.raw.setting_money's
// Python str.strip(). Dart trim() differs for U+001C..U+001F and U+FEFF.
// Never replace the original row value or its canonical bytes with this view.
String _settingMoneyText(String value) {
  bool whitespace(int c) =>
      (c >= 0x09 && c <= 0x0d) ||
      (c >= 0x1c && c <= 0x20) ||
      c == 0x85 ||
      c == 0xa0 ||
      c == 0x1680 ||
      (c >= 0x2000 && c <= 0x200a) ||
      c == 0x2028 ||
      c == 0x2029 ||
      c == 0x202f ||
      c == 0x205f ||
      c == 0x3000;
  var start = 0, end = value.length;
  while (start < end && whitespace(value.codeUnitAt(start))) {
    start++;
  }
  while (end > start && whitespace(value.codeUnitAt(end - 1))) {
    end--;
  }
  return value.substring(start, end);
}

String primaryColumn(String table) => switch (table) {
      'card_payment_deferrals' => 'entry_payment_key',
      'notification_candidate_registrations' => 'registration_key',
      'app_settings' || 'app_labels' => 'key',
      _ => 'id',
    };

class TreeKey implements Comparable<TreeKey> {
  TreeKey._(this.tag, this.value);
  factory TreeKey.parse(Object? value, String table) {
    if (value is! List || value.length != 2 || value[1] is! String) {
      rejectSegment('KEY_INVALID');
    }
    final tag = primaryColumn(table) == 'id' ? 'i' : 't';
    if (value[0] != tag) rejectSegment('KEY_INVALID');
    scalarString(value[1] as String);
    if (tag == 'i') {
      final text = value[1] as String;
      if (text.length > 20 || !RegExp(r'^(0|-?[1-9][0-9]*)$').hasMatch(text)) {
        rejectSegment('KEY_INVALID');
      }
      final n = BigInt.parse(text);
      if (n < minSigned64 || n > maxSigned64) rejectSegment('KEY_INVALID');
    }
    return TreeKey._(tag, value[1] as String);
  }
  final String tag, value;
  @override
  int compareTo(TreeKey other) {
    if (tag != other.tag) rejectSegment('KEY_INVALID');
    return tag == 'i'
        ? BigInt.parse(value).compareTo(BigInt.parse(other.value))
        : scalarCompare(value, other.value);
  }
}

class TreeDescriptor {
  TreeDescriptor._(
      this.ref, this.height, this.count, this.minimum, this.maximum);
  factory TreeDescriptor.parse(Object? value, String table) {
    final v = record(value, ['ref', 'height', 'count', 'min', 'max']);
    final height = v['height'];
    final count = int.parse(u64(v['count']));
    if (height is! int || height < 0 || height > 63) {
      rejectSegment('DESCRIPTOR_INVALID');
    }
    final low = v['min'] == null ? null : TreeKey.parse(v['min'], table);
    final high = v['max'] == null ? null : TreeKey.parse(v['max'], table);
    if (count == 0
        ? (height != 0 || low != null || high != null)
        : (low == null || high == null || low.compareTo(high) > 0)) {
      rejectSegment('DESCRIPTOR_INVALID');
    }
    return TreeDescriptor._(
        ObjectRef.parse(v['ref']), height, count, low, high);
  }
  final ObjectRef ref;
  final int height, count;
  final TreeKey? minimum, maximum;
}

class TypedObjectReference {
  const TypedObjectReference(this.ref, this.kinds,
      {this.table, this.descriptor});
  final ObjectRef ref;
  final Set<String> kinds;
  final String? table;
  final TreeDescriptor? descriptor;
}

// Validated local object ONLY. Not a membership/authorization/completeness receipt.
class VerifiedObject {
  VerifiedObject._(this.ref, this.kind, this._bytes, this.children);
  static const validatorBuild = 'segmented-e1/1';
  final ObjectRef ref;
  final String kind;
  final Uint8List _bytes;
  final List<TypedObjectReference> children;
  Uint8List get bytes => Uint8List.fromList(_bytes);
  Map<String, dynamic> get body => decodeC1(_bytes) as Map<String, dynamic>;

  static VerifiedObject verify(
      List<int> input, ObjectRef expected, CacheNamespace cache,
      {Set<String> kinds = transferableKinds,
      int maxBytes = 64 * 1024 * 1024}) {
    if (input.length > maxBytes || expected.byteLength > maxBytes) {
      rejectSegment('LOCAL_OBJECT_BUDGET');
    }
    if (input.length != expected.byteLength) {
      rejectSegment('OBJECT_LENGTH_INVALID');
    }
    // Own the bytes before checking; callers cannot mutate a verification receipt.
    final raw = Uint8List.fromList(input);
    final value = decodeC1(raw);
    if (value is! Map<String, dynamic>) rejectSegment('SHAPE_INVALID');
    final kind = value['kind'];
    if (kind is! String ||
        !transferableKinds.contains(kind) ||
        !kinds.contains(kind)) {
      rejectSegment('OBJECT_KIND_INVALID');
    }
    if (objectHash(kind, raw) != expected.hash) {
      rejectSegment('OBJECT_HASH_INVALID');
    }
    if (!SyncNamespace.parse(value['ns']).matches(cache.ns)) {
      rejectSegment('CACHE_CONTEXT_MISMATCH');
    }
    if (value['canon'] is! int || value['canon'] != 1) {
      rejectSegment('UNSUPPORTED_CONTRACT');
    }
    final children = <TypedObjectReference>[];
    const common = ['kind', 'ns', 'canon', 'raw_schema'];
    void add(ObjectRef ref, Set<String> kinds,
        {String? table, TreeDescriptor? descriptor}) {
      if (children.any((c) => c.ref.hash == ref.hash)) {
        rejectSegment('EDGE_INVALID');
      }
      children.add(TypedObjectReference(ref, Set.unmodifiable(kinds),
          table: table, descriptor: descriptor));
    }

    void treeChild(TreeDescriptor d, String table) =>
        add(d.ref, {d.height == 0 ? 'snapshot-leaf' : 'snapshot-node'},
            table: table, descriptor: d);
    if (kind != 'hot' &&
        kind != 'control' &&
        value['raw_schema'] != cache.versions.rawSchema) {
      rejectSegment('UNSUPPORTED_CONTRACT');
    }
    try {
      if (kind == 'raw-root') {
        record(value, [...common, 'tables']);
        final tables = value['tables'];
        if (tables is! List || tables.length != segmentedTables.length) {
          rejectSegment('TABLES_INVALID');
        }
        for (var i = 0; i < tables.length; i++) {
          final entry = record(tables[i], ['name', 'root', 'count']);
          final table = segmentedTables[i];
          if (entry['name'] != table) rejectSegment('TABLES_INVALID');
          final d = TreeDescriptor.parse(entry['root'], table);
          if (u64(entry['count']) != d.count.toString()) {
            rejectSegment('COUNT_INVALID');
          }
          treeChild(d, table);
        }
      } else if (kind.startsWith('snapshot-')) {
        final table = value['table'];
        if (table is! String || !segmentedTables.contains(table)) {
          rejectSegment('TABLE_INVALID');
        }
        record(value, [
          ...common,
          'table',
          'height',
          'count',
          'min',
          'max',
          ...(kind == 'snapshot-leaf' ? ['rows', 'oversized'] : ['children'])
        ]);
        final d = TreeDescriptor.parse({
          'ref': expected.toJson(),
          for (final f in ['height', 'count', 'min', 'max']) f: value[f]
        }, table);
        if (kind == 'snapshot-leaf') {
          final rows = value['rows'];
          final oversized = value['oversized'];
          if (d.height != 0 ||
              rows is! List ||
              d.count != rows.length ||
              rows.length > 256 ||
              oversized is! bool) {
            rejectSegment('LEAF_INVALID');
          }
          // Server tests the ordinary (false) header; 'true' is one byte shorter.
          final ordinaryBytes = raw.length + (oversized ? 1 : 0);
          if (oversized != (rows.length == 1 && ordinaryBytes > 262144) ||
              (!oversized && raw.length > 262144)) {
            rejectSegment('LEAF_BUDGET_INVALID');
          }
          TreeKey? previous;
          for (final item in rows) {
            final row = record(item, ['key', 'value']);
            final key = TreeKey.parse(row['key'], table);
            validateBundleShape(row['value'], '@Snapshot_$table');
            final fields = row['value'] as Map<String, dynamic>;
            if (key.value != fields[primaryColumn(table)].toString() ||
                (previous != null && previous.compareTo(key) >= 0)) {
              rejectSegment('ROW_KEY_INVALID');
            }
            if (table == 'app_settings') {
              if (['share_pin_hash', 'share_pin_is_default']
                  .contains(fields['key'])) {
                rejectSegment('SENSITIVE_SETTING_INVALID');
              }
              if ([
                'scheduled_income',
                'cash_flow_balance',
                'card_limit',
                'base_next_month_liquidity',
                'liquidity_status'
              ].contains(fields['key'])) {
                final text = _settingMoneyText(fields['value'] as String);
                if (!RegExp(r'^[+-]?[0-9]+(?:\.0+)?$').hasMatch(text) ||
                    BigInt.parse(text.split('.')[0]).abs() >
                        BigInt.from(maxExactMoney)) {
                  rejectSegment('MONEY_STRING_INVALID');
                }
              }
              if (fields['key'] == 'last_closed_month' &&
                  !validDate('${fields['value']}-01')) {
                rejectSegment('ROW_INVALID');
              }
            }
            if (table == 'card_payment_allocations' &&
                (fields['amount_value'] as num) < 0) {
              rejectSegment('ROW_INVALID');
            }
            if (identical(item, rows.first) && d.minimum!.compareTo(key) != 0) {
              rejectSegment('RANGE_INVALID');
            }
            previous = key;
          }
          if (previous != null && d.maximum!.compareTo(previous) != 0) {
            rejectSegment('RANGE_INVALID');
          }
        } else {
          final nodes = value['children'];
          // Root vs non-root minimum fanout is a membership check for E3.
          if (d.height == 0 ||
              nodes is! List ||
              nodes.length < 2 ||
              nodes.length > 32) {
            rejectSegment('NODE_INVALID');
          }
          TreeDescriptor? previous;
          var count = BigInt.zero;
          for (final item in nodes) {
            final child = TreeDescriptor.parse(item, table);
            if (child.count == 0 ||
                child.height + 1 != d.height ||
                (previous != null &&
                    previous.maximum!.compareTo(child.minimum!) >= 0)) {
              rejectSegment('NODE_INVALID');
            }
            if (previous == null && d.minimum!.compareTo(child.minimum!) != 0) {
              rejectSegment('RANGE_INVALID');
            }
            count += BigInt.from(child.count);
            previous = child;
            treeChild(child, table);
          }
          if (count.toString() != value['count'] ||
              d.maximum!.compareTo(previous!.maximum!) != 0) {
            rejectSegment('COUNT_INVALID');
          }
        }
      } else if (kind.startsWith('index-')) {
        const indexCommon = [...common, 'structural', 'count'];
        if (value['structural'] is! int || value['structural'] != 1) {
          rejectSegment('UNSUPPORTED_CONTRACT');
        }
        final count = int.parse(u64(value['count']));
        if (kind == 'index-root') {
          record(value, [...indexCommon, 'facts']);
          add(ObjectRef.parse(value['facts']),
              count == 0 ? {'index-empty'} : {'index-leaf', 'index-node'});
        } else if (kind == 'index-empty') {
          record(value, indexCommon);
          if (count != 0) rejectSegment('COUNT_INVALID');
        } else if (kind == 'index-node') {
          record(value, [...indexCommon, 'prefix', 'left', 'right']);
          final prefix = value['prefix'];
          if (prefix is! String ||
              prefix.length > 255 ||
              !RegExp(r'^[01]*$').hasMatch(prefix) ||
              count < 2) {
            rejectSegment('INDEX_INVALID');
          }
          for (final side in ['left', 'right']) {
            add(ObjectRef.parse(value[side]), {'index-leaf', 'index-node'});
          }
        } else {
          record(value, [...indexCommon, 'digest', 'facts']);
          final digest = hashValue(value['digest']);
          final facts = value['facts'];
          if (facts is! List || count == 0 || count != facts.length) {
            rejectSegment('INDEX_INVALID');
          }
          Uint8List? previous;
          for (final item in facts) {
            final fact = record(item, ['key', 'value']);
            if (fact['key'] is! List) rejectSegment('INDEX_INVALID');
            final bytes = encodeC1(fact['key']);
            if (objectHash('fact-key', bytes) != digest ||
                (previous != null && byteCompare(previous, bytes) >= 0)) {
              rejectSegment('FACT_INVALID');
            }
            previous = bytes;
          }
        }
      } else if (kind == 'hot') {
        record(value,
            ['kind', 'ns', 'canon', 'projection_schema', 'context', 'state']);
        final context = FinancialContext.parse(value['context']);
        const ReleaseContract().verify(cache.versions, context);
        if (value['projection_schema'] != cache.versions.projectionSchema) {
          rejectSegment('UNSUPPORTED_CONTRACT');
        }
        validateBundleShape(value['state'], '@AuthoritativeProjections');
      } else {
        record(value, [
          'kind',
          'ns',
          'canon',
          'snapshot_schema',
          'recurring_ownership_version',
          'exported_at',
          'range',
          'card_charge_policy',
          'columns',
          'discount_policy_defaults'
        ]);
        if (value['snapshot_schema'] is! int ||
            value['snapshot_schema'] != 7 ||
            value['recurring_ownership_version'] is! int ||
            value['recurring_ownership_version'] != 1) {
          rejectSegment('UNSUPPORTED_CONTRACT');
        }
        wireTime(value['exported_at']);
        validateBundleShape(value['range'], '@SnapshotRange');
        validateBundleShape(value['card_charge_policy'], '@SnapshotPolicy');
        validateBundleShape(
            value['discount_policy_defaults'], '@DiscountPolicyDefaults');
        final columns = record(value['columns'], segmentedTables);
        for (final table in segmentedTables) {
          final expectedColumns = bundleWireShapes['Snapshot_$table']!
              .keys
              .toList()
            ..sort(scalarCompare);
          if (!sameBytes(encodeC1(columns[table]), encodeC1(expectedColumns))) {
            rejectSegment('COLUMNS_INVALID');
          }
        }
      }
    } on FormatException {
      rejectSegment('SHAPE_INVALID');
    }
    return VerifiedObject._(expected, kind, raw, List.unmodifiable(children));
  }
}
