// This corpus classifies the manipulated invariant BEFORE parsing. It does not
// classify a rejection as A/B or an acceptance as C based on parser results.
// Synthetic re-sealing is not authentication or server-origin evidence.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/authoritative_bundle_contract.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'authoritative_bundle_test.dart'
    show baseline, owner, parentAt, parseWire, reseal, specimen;

Map<String, dynamic> copyWire(Map wire) => jsonDecode(jsonEncode(wire));

Object mutation(Object? value) => value == null
    ? 1
    : value is num
        ? value + 1
        : value is bool
            ? !value
            : '${value}_CONFLICT';

void main() {
  test('classified A/B safety and C-only server projection corpus', () async {
    final original = jsonDecode(
        File('test/fixtures/authoritative_bundle/identity_edges.json')
            .readAsStringSync()) as Map<String, dynamic>;
    final results = <Map<String, dynamic>>[];
    final invalidBodies = <Map<String, dynamic>>[];
    void check(String name, String category, String invariant,
        void Function(Map<String, dynamic>) change,
        {Map<String, dynamic>? base}) {
      final wire = copyWire(base ?? original);
      change(wire);
      reseal(wire);
      var accepted = false;
      try {
        parseWire(wire).toCoherentBundle(owner);
        accepted = true;
      } on FormatException {
        // Reject before candidate construction/publication.
      }
      results.add({
        'name': name,
        'category': category,
        'invariant': invariant,
        'mobile_accept': accepted,
        'trusted_origin_proven': false,
      });
      expect(accepted, category == 'C', reason: '$name: $invariant');
      if (category != 'C') invalidBodies.add(wire);
    }

    // 7 keyed collections x 3 source positions x 3 insert positions x 4
    // variants, plus 4 policy scopes x 4 variants: the 268-attack mechanism.
    final collections = <String, List<Object>>{
      'entries': ['state', 'entries'],
      'confirmed': ['state', 'confirmed_planned_entries'],
      'panels': ['state', 'panels'],
      'cash': ['state', 'cash_flows'],
      'events': ['state', 'card_payment_status', 'events'],
      'payment_rows': ['state', 'card_payment_status', 'rows'],
      'close': ['state', 'month_close_status', 'unconfirmed_recurring_items'],
    };
    dynamic at(Map wire, List<Object> path) {
      dynamic value = wire;
      for (final key in path) {
        value = value[key];
      }
      return value;
    }

    for (final entry in collections.entries) {
      for (var source = 0; source < 3; source++) {
        for (var placement = 0; placement < 3; placement++) {
          for (final variant in [
            'exact',
            'conflicting',
            'three',
            'reordered'
          ]) {
            check('duplicate/${entry.key}/$source/$placement/$variant', 'B',
                'namespace-specific primary identity uniqueness', (wire) {
              final rows = at(wire, entry.value) as List;
              expect(rows, isNotEmpty);
              final index = [0, rows.length ~/ 2, rows.length - 1][source];
              final extra = jsonDecode(jsonEncode(rows[index])) as Map;
              if (variant == 'conflicting') {
                final field = extra.containsKey('title') ? 'title' : 'note';
                extra[field] = 'CONFLICT';
              }
              rows.insert([0, rows.length ~/ 2, rows.length][placement], extra);
              if (variant == 'three') rows.add(jsonDecode(jsonEncode(extra)));
              if (variant == 'reordered') {
                rows.setAll(0, rows.reversed.toList());
              }
            });
          }
        }
      }
    }
    for (final scope in ['owner', 'family', 'toll', 'transit']) {
      for (final variant in ['exact', 'conflicting', 'three', 'reordered']) {
        check('duplicate/binding/$scope/$variant', 'B',
            'Snapshot-compatible canonical policy bindings', (w) {
          final rows =
              w['snapshot']['card_charge_policy']['cards'][scope] as List;
          final extra = jsonDecode(jsonEncode(rows.first)) as Map;
          if (variant == 'conflicting') extra['parameters']['rate'] = '0.02';
          rows.add(extra);
          if (variant == 'three') rows.add(jsonDecode(jsonEncode(extra)));
          if (variant == 'reordered') rows.setAll(0, rows.reversed.toList());
        });
      }
    }

    Iterable<List<Object>> finite(Object? value, List<Object> path) sync* {
      if (value is Map) {
        for (final key in value.keys) {
          if (['book_section', 'event_type', 'target', 'rounding']
                  .contains(key) ||
              (key == 'type' &&
                  (path.contains('card_charge_policy') ||
                      path.contains('projection_policy')))) {
            yield [...path, key as String];
          }
          yield* finite(value[key], [...path, key as String]);
        }
      } else if (value is List) {
        for (var i = 0; i < value.length; i++) {
          yield* finite(value[i], [...path, i]);
        }
      }
    }

    for (final base in [original, specimen()]) {
      for (final path in finite(base, [])) {
        check(
            'finite/${results.length}/${path.join('.')}',
            'B',
            'supported storage/descriptor domain',
            (w) => parentAt(w, path)[path.last] = 'CORRUPT',
            base: base);
      }
    }

    for (final pair in [
      ('entries', 'LedgerEntry', 'Snapshot_ledger_entries'),
      ('confirmed_planned_entries', 'LedgerEntry', 'Snapshot_ledger_entries'),
      ('panels', 'MonthlyPanel', 'Snapshot_monthly_panels'),
      ('cash_flows', 'CashFlow', 'Snapshot_cash_flows'),
    ]) {
      final fields = bundleWireShapes[pair.$2]!
          .keys
          .where(bundleWireShapes[pair.$3]!.containsKey);
      final rows = original['state'][pair.$1] as List;
      for (var i = 0; i < rows.length; i++) {
        for (final field in fields) {
          check(
              'raw/${pair.$1}/$i/$field',
              'B',
              'same supplied raw entity complete shared-field equality',
              (w) => w['state'][pair.$1][i][field] = mutation(rows[i][field]));
        }
      }
      for (var i = 0; i < rows.length; i++) {
        check('selection/${pair.$1}/omit/$i', 'C', 'server-selected membership',
            (w) => (w['state'][pair.$1] as List).removeAt(i));
      }
      check('selection/${pair.$1}/empty', 'C', 'server-selected membership',
          (w) => w['state'][pair.$1] = []);
      check(
          'selection/${pair.$1}/reverse',
          'C',
          'server-selected ordering',
          (w) => w['state'][pair.$1] =
              (w['state'][pair.$1] as List).reversed.toList());
    }
    for (final rate in ['0.02', '0.0120']) {
      check('policy/agreed-noncanonical/$rate', 'B',
          'Snapshot restore registry exact-definition compatibility', (w) {
        w['snapshot']['card_charge_policy']['cards']['owner'][0]['parameters']
            ['rate'] = rate;
        w['state']['owner_discount_month']['projection_policy']['parameters']
            ['rate'] = rate;
      });
    }
    check('reference/close/missing', 'B', 'referenced source exists', (w) {
      w['state']['month_close_status']['unconfirmed_recurring_items'][0]['id'] =
          999999;
    });
    check('reference/payment/missing', 'B', 'referenced member exists', (w) {
      w['state']['card_payment_status']['rows'][0]['entry_ids'][0] = 999999;
    });
    check('reference/source/current-and-confirmed', 'B',
        'same installed ledger identity cannot repeat', (w) {
      w['state']['entries'].add(
          jsonDecode(jsonEncode(w['state']['confirmed_planned_entries'][0])));
    });
    final close = original['state']['month_close_status']
        ['unconfirmed_recurring_items'] as List;
    for (var i = 0; i < close.length; i++) {
      check(
          'N1/omit/$i',
          'C',
          'server close eligibility/selection',
          (w) => (w['state']['month_close_status']
                  ['unconfirmed_recurring_items'] as List)
              .removeAt(i));
    }
    check(
        'N1/empty',
        'C',
        'server close eligibility/selection',
        (w) => w['state']['month_close_status']
            ['unconfirmed_recurring_items'] = []);
    check(
        'N1/order',
        'C',
        'server close order',
        (w) => w['state']['month_close_status']['unconfirmed_recurring_items'] =
            close.reversed.toList());
    check('N2/split-toll-group', 'C', 'server grouping partition', (w) {
      final rows = w['state']['card_payment_status']['rows'] as List;
      final group = rows.singleWhere((r) => r['is_group'] == true);
      final splits = <Map>[];
      for (final id in group['entry_ids']) {
        final raw = (w['snapshot']['data']['ledger_entries'] as List)
            .singleWhere((r) => r['id'] == id);
        final part = (group['payment_parts'] as List)
            .singleWhere((p) => p['entry_id'] == id);
        splits.add({
          ...group,
          ...raw,
          'is_group': false,
          'original_amount': raw['amount_value'],
          'entry_ids': [id],
          'payment_keys': [raw['payment_key']],
          'payment_parts': [part],
          'remaining_amount': part['remaining_amount']
        });
      }
      rows.remove(group);
      rows.addAll(splits);
    }, base: specimen());
    check('alias/group-principal', 'B', 'same explicit principal aliases', (w) {
      final group = (w['state']['card_payment_status']['rows'] as List)
          .singleWhere((r) => r['is_group'] == true);
      group['amount_value'] += 1;
    }, base: specimen());
    for (final key in [
      'confirmed_effective_discount_amount',
      'confirmed_effective_amount_value'
    ]) {
      check('N3/archived/$key', 'C', 'backend policy-dependent archived actual',
          (w) => w['state']['confirmed_planned_entries'][0][key] += 1,
          base: specimen());
    }
    // Actual isolated publication/readback consumers, not a parser-only claim.
    // Diagnostic acquisition itself remains nonpublishing.
    final existing =
        await Directory.systemTemp.createTemp('mn-boundary-existing-');
    final empty = await Directory.systemTemp.createTemp('mn-boundary-empty-');
    addTearDown(() => existing.delete(recursive: true));
    addTearDown(() => empty.delete(recursive: true));
    final oldStore = OfflineStore(directoryProvider: () async => existing);
    final emptyStore = OfflineStore(directoryProvider: () async => empty);
    final originalBaseline =
        baseline(parseWire(original).toCoherentBundle(owner));
    await oldStore.replaceBaseline(originalBaseline);
    final file = File('${existing.path}/offline-mode/baseline.json');
    final before = await file.readAsBytes();
    for (final wire in invalidBodies) {
      for (final store in [oldStore, emptyStore]) {
        var installed = false;
        Future<void> consume() async {
          final candidate = parseWire(wire).toCoherentBundle(owner);
          await store.replaceBaseline(baseline(candidate));
          installed = true;
        }

        await expectLater(consume(), throwsFormatException);
        expect(installed, false);
      }
      expect(await file.readAsBytes(), before);
      expect(
          (await oldStore.loadBaseline())!.toJson(), originalBaseline.toJson());
      expect(await emptyStore.loadBaseline(), isNull);
      expect(await File('${empty.path}/offline-mode/baseline.json').exists(),
          false);
    }
    const output = String.fromEnvironment('BOUNDARY_MATRIX_OUTPUT');
    if (output.isNotEmpty) {
      await File(output).writeAsString(
          jsonEncode({
            'cases': results,
            'ab_invalid': results.where((r) => r['category'] != 'C').length,
            'c_only': results.where((r) => r['category'] == 'C').length,
            'publication_checks': invalidBodies.length * 2,
          }),
          flush: true);
    }
  }, timeout: const Timeout(Duration(minutes: 3)));
}
