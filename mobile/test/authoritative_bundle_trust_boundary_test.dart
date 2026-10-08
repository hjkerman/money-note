import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/coherent_refresh_coordinator.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'authoritative_bundle_test.dart'
    show baseline, owner, parseWire, reseal, specimen;

List<Map<String, dynamic>> idempotencyCases() =>
    (jsonDecode(File('test/fixtures/bundle_idempotency_keys.json')
            .readAsStringSync()) as List)
        .cast<Map<String, dynamic>>();

Map<String, dynamic> withEventKeys(List keys) {
  final w = specimen();
  final events = w['snapshot']['data']['card_payment_events'] as List;
  final first = events.first as Map;
  first['idempotency_key'] = keys.first;
  for (final event in w['state']['card_payment_status']['events']) {
    if (event['id'] == first['id']) event['idempotency_key'] = keys.first;
  }
  events.add({
    ...first,
    'id': 900001,
    'batch_id': null,
    'event_type': 'discount',
    'total_amount': 0,
    'cash_flow_id': null,
    'idempotency_key': keys.last,
    'request_fingerprint': null,
  });
  reseal(w);
  return w;
}

void main() {
  for (final c in idempotencyCases()) {
    test('N4 migrated BINARY key contract: ${c['name']}', () {
      final w = withEventKeys(c['keys']);
      if (c['accept'] == true) {
        expect(() => parseWire(w).toCoherentBundle(owner), returnsNormally);
      } else {
        expect(
            () => parseWire(w).toCoherentBundle(owner), throwsFormatException);
      }
    });
  }

  for (final c in idempotencyCases().where((c) => c['accept'] == false)) {
    for (final existing in [false, true]) {
      test('N4 rejects before actual publication: ${c['name']}/$existing',
          () async {
        final dir = await Directory.systemTemp.createTemp('mn-n4-publication-');
        addTearDown(() => dir.delete(recursive: true));
        final store = OfflineStore(directoryProvider: () async => dir);
        final file = File('${dir.path}/offline-mode/baseline.json');
        if (existing) {
          await store.replaceBaseline(
              baseline(parseWire(specimen()).toCoherentBundle(owner)));
        }
        final before = existing ? await file.readAsBytes() : null;
        var installed = false;
        final api = MoneyNoteApiClient(
            baseUrl: 'http://synthetic.invalid',
            client: MockClient((_) async => http.Response.bytes(
                utf8.encode(jsonEncode(withEventKeys(c['keys']))), 200)));
        final coordinator = CoherentRefreshCoordinator(api,
            localToday: () => '2026-10-05',
            formatDate: (d) => d.toIso8601String().substring(0, 10));
        final ticket = coordinator.begin(1, 1);
        Future<void> consume() async {
          final bundle = await coordinator.acquireBundleForDiagnostics(
              () => owner,
              ticket: ticket,
              currentLineageGeneration: () => 1,
              currentAuthenticationGeneration: () => 1,
              modeAllowed: () => true);
          await store.replaceBaseline(baseline(bundle), beforePublish: () {
            if (!coordinator.mayInstall(ticket,
                currentLineageGeneration: 1,
                currentAuthenticationGeneration: 1,
                modeAllowed: true)) {
              throw StateError('stale publication');
            }
          });
          installed = true;
        }

        await expectLater(consume(), throwsA(isA<MoneyNoteApiException>()));
        expect(installed, false);
        if (existing) {
          expect(await file.readAsBytes(), before);
          expect(await store.loadBaseline(), isNotNull);
        } else {
          expect(await file.exists(), false);
          expect(await store.loadBaseline(), isNull);
        }
      });
    }
  }

  test('valid null keys reach candidate and durable readback unchanged',
      () async {
    final dir = await Directory.systemTemp.createTemp('mn-n4-valid-');
    addTearDown(() => dir.delete(recursive: true));
    final store = OfflineStore(directoryProvider: () async => dir);
    final accepted = baseline(
        parseWire(withEventKeys([null, null])).toCoherentBundle(owner));
    await store.replaceBaseline(accepted);
    expect((await store.loadBaseline())!.toJson(), accepted.toJson());
  });

  // These are deliberately edited synthetic bodies, NOT proven server-origin
  // responses. They characterize C-only trust, not backend calculation truth.
  for (final section in [
    'entries',
    'confirmed_planned_entries',
    'panels',
    'cash_flows'
  ]) {
    test('C selected collection is not independently reconstructed: $section',
        () {
      final w = specimen();
      w['state'][section] = [];
      expect(() => parseWire(w), returnsNormally);
    });
    test('C selected collection order is server-owned: $section', () {
      final w = specimen();
      w['state'][section] = (w['state'][section] as List).reversed.toList();
      expect(() => parseWire(w), returnsNormally);
    });
  }
  test('C composite payment presentation is not a raw first-member entity', () {
    final w = specimen();
    final group = (w['state']['card_payment_status']['rows'] as List)
        .singleWhere((row) => row['is_group'] == true);
    group['title'] = 'Server-provided presentation';
    group['amount_value'] += 1;
    group['original_amount'] += 1;
    expect(() => parseWire(w), returnsNormally);
  });
  test('C group remaining is not recomputed from payment parts', () {
    final w = specimen();
    final group = (w['state']['card_payment_status']['rows'] as List)
        .singleWhere((row) => row['is_group'] == true);
    group['remaining_amount'] += 1;
    expect(() => parseWire(w), returnsNormally);
  });
  for (final attack in ['empty', 'omit', 'reverse', 'future source']) {
    test('N1 C-only close selection: $attack', () {
      final w = specimen();
      final items = w['state']['month_close_status']
          ['unconfirmed_recurring_items'] as List;
      if (attack == 'empty') {
        items.clear();
      } else if (attack == 'omit') {
        expect(items, isNotEmpty);
        items.removeAt(0);
      } else if (attack == 'reverse') {
        w['state']['month_close_status']['unconfirmed_recurring_items'] =
            items.reversed.toList();
      } else {
        final item = items.first;
        final table =
            item['kind'] == 'fixed' ? 'monthly_panels' : 'ledger_entries';
        (w['snapshot']['data'][table] as List)
                .singleWhere((r) => r['id'] == item['id'])['created_at'] =
            '2026-11-01 00:00:00';
        reseal(w);
      }
      expect(() => parseWire(w), returnsNormally);
    });
  }
  for (final attack in ['member order', 'row order']) {
    test('N2 C-only payment order: $attack', () {
      final w = specimen();
      final status = w['state']['card_payment_status'];
      if (attack == 'row order') {
        status['rows'] = (status['rows'] as List).reversed.toList();
      } else {
        final group =
            (status['rows'] as List).singleWhere((r) => r['is_group'] == true);
        for (final key in ['entry_ids', 'payment_keys', 'payment_parts']) {
          group[key] = (group[key] as List).reversed.toList();
        }
        group['id'] = -group['entry_ids'][0];
        group['payment_key'] = 'group:toll:${group['entry_ids'][0]}';
      }
      expect(() => parseWire(w), returnsNormally);
    });
  }
  test(
      'N2 non-toll partition selection is backend-owned, not reclassified locally',
      () {
    final w = specimen();
    final rows = w['state']['card_payment_status']['rows'] as List;
    final group = rows.singleWhere((r) => r['is_group'] == true);
    final single = rows.firstWhere((r) => r['is_group'] == false);
    expect(single['is_toll'], false);
    for (final key in ['entry_ids', 'payment_keys', 'payment_parts']) {
      (group[key] as List).addAll(single[key] as List);
    }
    rows.remove(single);
    expect(() => parseWire(w), returnsNormally);
  });
  for (final field in [
    'confirmed_effective_discount_amount',
    'confirmed_effective_amount_value'
  ]) {
    test('N3 archived derived actual is backend-owned: $field', () {
      final w = specimen();
      final confirmed = w['state']['confirmed_planned_entries'][0];
      final child = (w['snapshot']['data']['ledger_entries'] as List)
          .singleWhere((r) => r['source_planned_entry_id'] == confirmed['id']);
      expect(child['book_section'], 'archive');
      expect((w['state']['entries'] as List).any((r) => r['id'] == child['id']),
          false);
      confirmed[field] += 1;
      expect(() => parseWire(w), returnsNormally);
    });
  }
  for (final group in [false, true]) {
    for (final field in ['remaining', 'discount']) {
      test(
          'N3 coordinated derived aliases are not financial proof: $group/$field',
          () {
        final w = specimen();
        final row = (w['state']['card_payment_status']['rows'] as List)
            .firstWhere((r) => r['is_group'] == group);
        if (field == 'remaining') {
          row['remaining_amount'] += 1;
          row['payment_parts'][0]['remaining_amount'] += 1;
        } else {
          row['discount_amount'] += 1;
          row['effective_discount_amount'] += 1;
        }
        expect(() => parseWire(w), returnsNormally);
      });
    }
  }
  test('N3 coordinated archived actual money is backend-owned', () {
    final w = specimen();
    final confirmed = w['state']['confirmed_planned_entries'][0];
    confirmed['confirmed_effective_discount_amount'] += 1;
    confirmed['confirmed_effective_amount_value'] -= 1;
    expect(() => parseWire(w), returnsNormally);
  });
  test('B same raw principal and identity contradictions still reject', () {
    for (final field in ['amount_value', 'id', 'discount_override']) {
      final w = specimen();
      w['state']['entries'][0][field] += 1;
      expect(() => parseWire(w), throwsFormatException, reason: field);
    }
  });
  test('B same server-computed single-entity aliases still agree', () {
    final w = specimen();
    final row = (w['state']['card_payment_status']['rows'] as List)
        .firstWhere((row) => row['is_group'] == false);
    row['payment_parts'][0]['remaining_amount'] += 1;
    expect(() => parseWire(w), throwsFormatException);
  });
  test('B group principal aliases agree without recalculating aggregation', () {
    final w = specimen();
    final group = (w['state']['card_payment_status']['rows'] as List)
        .singleWhere((r) => r['is_group'] == true);
    group['amount_value'] += 1;
    expect(() => parseWire(w), throwsFormatException);
  });
}
