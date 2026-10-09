import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/authoritative_bundle_contract.dart';
import 'package:money_note_mobile/src/authoritative_bundle_validation.dart';
import 'package:money_note_mobile/src/coherent_refresh_coordinator.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

Map<String, dynamic> specimen([String kind = 'rich']) =>
    jsonDecode(File('test/fixtures/authoritative_bundle_$kind.json')
        .readAsStringSync()) as Map<String, dynamic>;

AuthoritativeBundle parseWire(Map<String, dynamic> wire) =>
    AuthoritativeBundle.decode(utf8.encode(jsonEncode(wire)));

final owner = AuthUser(
    id: 1, username: 'owner', displayName: 'Owner', sharePinNeedsChange: false);

// Intentionally re-seal corrupted specimens so relationship tests are not
// accidentally satisfied merely by a stale hash rejection.
void reseal(Map<String, dynamic> wire) {
  final s = wire['snapshot'];
  final data = s['data'] as Map<String, dynamic>;
  final m = s['manifest'];
  for (final table in data.keys) {
    m['tables'][table]['row_count'] = data[table].length;
    m['tables'][table]['sha256'] = bundleHash(data[table]);
  }
  m['data_sha256'] = bundleHash(data);
  m['card_charge_policy_sha256'] = bundleHash(s['card_charge_policy']);
  m['content_sha256'] = bundleHash({
    for (final key in [
      'schema_version',
      'recurring_ownership_version',
      'exported_at',
      'range',
      'card_charge_policy',
      'data'
    ])
      key: s[key],
  });
  s['snapshot_id'] = m['content_sha256'];
  wire['authority']['state_fingerprint'] = bundleHash({
    for (final key in ['schema_version', 'range', 'card_charge_policy', 'data'])
      key: s[key],
  });
}

Iterable<List<Object>> requiredPaths(Object? value, String spec,
    [List<Object> path = const []]) sync* {
  if (spec.startsWith('?')) {
    if (value == null) return;
    spec = spec.substring(1);
  }
  if (spec.contains('|') && !spec.startsWith('[') && !spec.startsWith('{')) {
    spec = spec.split('|').firstWhere((option) {
      try {
        validateBundleShape(value, option);
        return true;
      } on FormatException {
        return false;
      }
    });
  }
  if (spec.startsWith('@')) {
    final fields = bundleWireShapes[spec.substring(1)]!;
    for (final field in fields.entries) {
      final next = [...path, field.key];
      yield next;
      yield* requiredPaths((value as Map)[field.key], field.value, next);
    }
  } else if (spec.startsWith('[')) {
    final rows = value as List;
    for (var i = 0; i < rows.length; i++) {
      yield* requiredPaths(
          rows[i], spec.substring(1, spec.length - 1), [...path, i]);
    }
  }
}

dynamic parentAt(Map<String, dynamic> wire, List<Object> path) {
  dynamic value = wire;
  for (final key in path.take(path.length - 1)) {
    value = value[key];
  }
  return value;
}

OfflineBaseline baseline(CoherentRefreshBundle bundle) {
  final c = bundle.candidate;
  final e = bundle.envelope;
  return OfflineBaseline(
      syncedAt: DateTime.utc(2026, 10, 5),
      user: c.user,
      summary: c.summary,
      cardPaymentStatus: c.cardPaymentStatus,
      judgment: c.judgment,
      monthCloseStatus: c.monthCloseStatus,
      settings: c.settings,
      ownerDiscountMonth: c.ownerDiscountMonth,
      familyDiscountMonth: c.familyDiscountMonth,
      transitDiscountProfile: c.transitDiscountProfile,
      entries: c.entries,
      confirmedPlannedEntries: c.confirmedPlannedEntries,
      panels: c.panels,
      cashFlows: c.cashFlows,
      authoritativeSnapshot: e.snapshot,
      serverStateFingerprint: e.fingerprint,
      discountPolicyDefaults: e.discountPolicyDefaults);
}

void main() {
  test('server-approved canonical edge body is accepted without repair', () {
    expect(() => parseWire(specimen('canonical_edges')), returnsNormally);
  });
  test('conditional actual/effective money cannot fall back to a template', () {
    for (final path in <List<Object>>[
      [
        'state',
        'confirmed_planned_entries',
        0,
        'confirmed_effective_discount_amount'
      ],
      [
        'state',
        'confirmed_planned_entries',
        0,
        'confirmed_effective_amount_value'
      ],
      ['state', 'entries', 0, 'effective_amount_value'],
      ['state', 'panels', 0, 'effective_amount_value'],
    ]) {
      final wire = specimen();
      parentAt(wire, path)[path.last] = null;
      expect(() => parseWire(wire), throwsFormatException,
          reason: path.join('.'));
    }
  });
  test('opaque policy definitions still require their declared parameters', () {
    final wire = specimen();
    wire['snapshot']['card_charge_policy']['cards']['owner'][0]['parameters']
        .remove('rate');
    reseal(wire);
    expect(() => parseWire(wire), throwsFormatException);
  });

  test('payment projection member IDs cannot contradict the payment parts', () {
    final wire = specimen();
    wire['state']['card_payment_status']['rows'][0]['entry_ids'] = [999];
    expect(() => parseWire(wire), throwsFormatException);
  });

  test('diagnostic acquisition propagates HTTP authorization failure',
      () async {
    final api = MoneyNoteApiClient(
        baseUrl: 'http://synthetic.invalid',
        client: MockClient(
            (_) async => http.Response('{"detail":"expired"}', 401)));
    final c = CoherentRefreshCoordinator(api,
        localToday: () => '2026-10-05',
        formatDate: (d) => d.toIso8601String().substring(0, 10));
    final ticket = c.begin(1, 1);
    await expectLater(
        c.acquireBundleForDiagnostics(() => owner,
            ticket: ticket,
            currentLineageGeneration: () => 1,
            currentAuthenticationGeneration: () => 1,
            modeAllowed: () => true),
        throwsA(isA<MoneyNoteApiException>()));
  });

  test('diagnostic acquisition rejects malformed bytes and disallowed mode',
      () async {
    var calls = 0;
    final api = MoneyNoteApiClient(
        baseUrl: 'http://synthetic.invalid',
        client: MockClient((_) async {
          calls++;
          return http.Response('{"bundle_version":1}', 200);
        }));
    final c = CoherentRefreshCoordinator(api,
        localToday: () => '2026-10-05',
        formatDate: (d) => d.toIso8601String().substring(0, 10));
    final ticket = c.begin(1, 1);
    await expectLater(
        c.acquireBundleForDiagnostics(() => owner,
            ticket: ticket,
            currentLineageGeneration: () => 1,
            currentAuthenticationGeneration: () => 1,
            modeAllowed: () => true),
        throwsA(isA<MoneyNoteApiException>()));
    expect(calls, 1);
    await expectLater(
        c.acquireBundleForDiagnostics(() => owner,
            ticket: ticket,
            currentLineageGeneration: () => 1,
            currentAuthenticationGeneration: () => 1,
            modeAllowed: () => false),
        throwsA(isA<MoneyNoteApiException>()));
    expect(calls, 1);
  });
  test('every declared nested field is required, including nullable fields',
      () {
    final paths = requiredPaths(specimen(), '@Bundle').toList();
    expect(paths.length, greaterThan(700));
    for (final path in paths) {
      final wire = specimen();
      parentAt(wire, path).remove(path.last);
      expect(() => parseWire(wire), throwsFormatException,
          reason: path.join('.'));
    }
  });

  test('Snapshot policy evidence cannot omit required nested fields', () {
    for (final path in <List<Object>>[
      ['snapshot', 'card_charge_policy', 'classifier', 'matching'],
      ['snapshot', 'card_charge_policy', 'profile_selectors', 'transit'],
    ]) {
      final wire = specimen();
      parentAt(wire, path).remove(path.last);
      reseal(wire);
      expect(() => parseWire(wire), throwsFormatException);
    }
  });

  test('canonical confirmed source may have a null mutable execution date', () {
    final wire = specimen();
    final source = (wire['snapshot']['data']['ledger_entries'] as List)
        .firstWhere((e) =>
            e['entry_kind'] == 'planned' && e['confirmed_month'] != null);
    source['entry_date'] = null;
    reseal(wire);
    expect(() => parseWire(wire), returnsNormally);
  });

  test('re-sealed malformed recurring/card/fixed identities still reject', () {
    final mutations = <String, void Function(Map<String, dynamic>)>{
      'missing recurring source': (w) {
        final e = (w['snapshot']['data']['ledger_entries'] as List)
            .firstWhere((r) => r['source_planned_entry_id'] != null);
        e['source_planned_entry_id'] = null;
      },
      'partial recurring epoch': (w) {
        final e = (w['snapshot']['data']['ledger_entries'] as List)
            .firstWhere((r) => r['source_planned_entry_id'] != null);
        e['confirmed_at'] = null;
      },
      'missing recurring principal': (w) {
        final e = (w['snapshot']['data']['ledger_entries'] as List)
            .firstWhere((r) => r['source_planned_entry_id'] != null);
        e['amount_value'] = null;
      },
      'duplicate child': (w) {
        final rows = w['snapshot']['data']['ledger_entries'] as List;
        final e = rows.firstWhere((r) => r['source_planned_entry_id'] != null);
        rows.add({...e, 'id': 900, 'payment_key': 'duplicate-child'});
      },
      'card batch wrong key': (w) {
        w['snapshot']['data']['card_payment_batch_items'][0]
            ['entry_payment_key'] = 'not-owned';
      },
      'allocation wrong event': (w) {
        w['snapshot']['data']['card_payment_allocations'][0]
            ['payment_event_id'] = 999;
      },
      'payment projection wrong child': (w) {
        w['state']['card_payment_status']['rows'][0]['payment_parts'][0]
            ['entry_id'] = 999;
      },
      'cash raw/projection mismatch': (w) {
        w['state']['cash_flows'][0]['amount_value']++;
      },
      'duplicate row ID': (w) {
        final rows = w['snapshot']['data']['ledger_entries'] as List;
        rows.add(Map<String, dynamic>.from(rows.first));
      },
      'fixed missing linked flow': (w) {
        final p = (w['snapshot']['data']['monthly_panels'] as List)
            .firstWhere((p) => p['panel_type'] == 'fixed');
        p['confirmed_cash_flow_id'] = 999;
      },
      'authority revision': (w) {
        w['authority']['state_revision'] = -1;
      },
      'evaluation date mismatch': (w) {
        w['authority']['evaluation_date'] = '2026-10-06';
      },
      'setting divergence': (w) {
        w['state']['settings']['card_limit'] = '1';
      },
    };
    for (final mutation in mutations.entries) {
      final wire = specimen();
      mutation.value(wire);
      reseal(wire);
      expect(() => parseWire(wire), throwsFormatException,
          reason: mutation.key);
    }
  });

  test('raw duplicate keys, hashes, principal and malformed containers reject',
      () {
    final text = jsonEncode(specimen());
    expect(
        () => AuthoritativeBundle.decode(utf8.encode(text.replaceFirst(
            '"bundle_version":1', '"bundle_version":1,"bundle_version":1'))),
        throwsFormatException);
    for (final path in <List<Object>>[
      ['state', 'entries'],
      ['state', 'judgment', 'category_labels'],
      ['state', 'month_close_status', 'needs_close'],
      ['state', 'card_payment_status', 'rows'],
      ['snapshot', 'snapshot_id'],
      ['authority', 'state_fingerprint'],
    ]) {
      final wire = specimen();
      parentAt(wire, path)[path.last] = null;
      expect(() => parseWire(wire), throwsFormatException);
    }
    final parsed = parseWire(specimen());
    expect(
        () => parsed.toCoherentBundle(AuthUser(
            id: 2,
            username: 'other',
            displayName: 'Other',
            sharePinNeedsChange: false)),
        throwsFormatException);
    expect(
        () => parsed.wire['state']['entries'].clear(), throwsUnsupportedError);
    final wrongHash = specimen();
    wrongHash['snapshot']['manifest']['data_sha256'] = '0' * 64;
    expect(() => parseWire(wrongHash), throwsFormatException);
  });

  test(
      'diagnostic parsing cannot publish or retire pending; durable baseline round-trip agrees',
      () async {
    final directory = await Directory.systemTemp.createTemp('mn-bundle-store-');
    addTearDown(() => directory.delete(recursive: true));
    final store = OfflineStore(directoryProvider: () async => directory);
    final pending = await store.beginOnlineWrite(owner.id);
    final parsed =
        AuthoritativeBundle.decode(utf8.encode(jsonEncode(specimen())));
    final b = baseline(parsed.toCoherentBundle(owner));
    expect(await store.loadBaseline(), isNull);
    expect(
        (await store.loadPendingOnlineWrite(owner.id))?.token, pending.token);
    await store.replaceBaseline(b);
    expect((await store.loadBaseline())!.toJson(), b.toJson());
    expect(
        (await store.loadPendingOnlineWrite(owner.id))?.token, pending.token);
  });
  test('valid zero false null and empty values are not absence', () {
    final parsed = parseWire(specimen('empty'));
    final bundle = parsed.toCoherentBundle(owner);
    expect(bundle.candidate.summary.cardTotal, 0);
    expect(bundle.candidate.entries, isEmpty);
    expect(bundle.candidate.monthCloseStatus.needsClose, false);
    expect(bundle.candidate.monthCloseStatus.lastClosedMonth, isNull);
  });

  test('required fields cannot be silently replaced by model defaults', () {
    final paths = <List<Object>>[
      ['bundle_version'],
      ['authority'],
      ['snapshot'],
      ['state'],
      ['principal'],
      ['authority', 'state_revision'],
      ['authority', 'state_fingerprint'],
      ['authority', 'evaluation_date'],
      ['authority', 'discount_policy_defaults', 'family'],
      ['state', 'summary', 'card_total'],
      ['state', 'summary', 'current_month_spendable'],
      ['state', 'entries', 0, 'automatic_discount_eligible'],
      ['state', 'entries', 0, 'effective_discount_amount'],
      ['state', 'confirmed_planned_entries', 0, 'confirmed_amount_value'],
      ['state', 'panels', 0, 'can_confirm_fixed'],
      ['state', 'cash_flows', 0, 'is_primary_income'],
      ['state', 'card_payment_status', 'rows'],
      ['state', 'card_payment_status', 'events'],
      ['state', 'owner_discount_month', 'projection_policy'],
      ['state', 'month_close_status', 'card_recurring_confirmation_available'],
      ['state', 'judgment', 'category_labels'],
      ['state', 'settings'],
      ['snapshot', 'manifest', 'data_sha256'],
      ['snapshot', 'data', 'ledger_entries'],
    ];
    for (final path in paths) {
      final wire = specimen();
      dynamic parent = wire;
      for (final key in path.take(path.length - 1)) {
        parent = parent[key];
      }
      parent.remove(path.last);
      expect(() => parseWire(wire), throwsFormatException,
          reason: path.join('.'));
    }
  });

  test('unknown bundle version and malformed types fail closed', () {
    for (final value in [null, false, '1', 0, 2]) {
      final wire = specimen()..['bundle_version'] = value;
      expect(() => parseWire(wire), throwsFormatException);
    }
    for (final value in [null, false, '100', 0.5, 9007199254740992]) {
      final wire = specimen();
      wire['state']['summary']['card_total'] = value;
      expect(() => parseWire(wire), throwsFormatException);
    }
  });

  test('near-integer and underflow raw tokens reject before JSON rounding', () {
    final original = jsonEncode(specimen('empty'));
    for (final token in [
      '-1e-400',
      '0.00000000000000001',
      '5000.00000000000001'
    ]) {
      final text =
          original.replaceFirst('"card_total":0', '"card_total":$token');
      expect(() => AuthoritativeBundle.decode(utf8.encode(text)),
          throwsFormatException);
    }
  });

  for (final kind in [
    'empty',
    'rich',
    'early',
    'boundary',
    'real',
    'closed',
    'canonical_edges'
  ]) {
    test('old/new typed candidate and durable baseline equivalent: $kind',
        () async {
      final wire = specimen(kind);
      final day = wire['authority']['evaluation_date'] as String;
      final month = day.substring(0, 7);
      final paths = {
        '/api/month/current/status': 'month_close_status',
        '/api/entries/current': 'entries',
        '/api/month/current/panels': 'panels',
        '/api/month/current/summary': 'summary',
        '/api/card-payments/current': 'card_payment_status',
        '/api/judgment/current': 'judgment',
        '/api/month/current/planned/confirmed': 'confirmed_planned_entries',
        '/api/settings': 'settings',
        '/api/cash-flows': 'cash_flows',
        '/api/card-discounts/profiles/transit/$month':
            'transit_discount_profile',
      };
      final calls = <String>[];
      final api = MoneyNoteApiClient(
          baseUrl: 'http://synthetic.invalid',
          client: MockClient((r) async {
            calls.add(r.url.path);
            dynamic value;
            if (r.url.path == '/api/offline-reconciliation/baseline') {
              value = {...wire['authority'], 'snapshot': wire['snapshot']};
            } else if (r.url.path == '/api/authoritative-state') {
              value = wire;
            } else if (r.url.path == '/api/card-discounts/months/$month') {
              value = wire['state']
                  ['${r.url.queryParameters['scope']}_discount_month'];
            } else {
              value = wire['state'][paths[r.url.path]];
            }
            return http.Response.bytes(utf8.encode(jsonEncode(value)), 200);
          }));
      final coordinator = CoherentRefreshCoordinator(api,
          localToday: () => day,
          formatDate: (d) => d.toIso8601String().substring(0, 10));
      final old = await coordinator.acquireLegacyForDiagnostics(() => owner);
      expect(calls.length, 14);
      expect(calls, isNot(contains('/api/authoritative-state')));
      final ticket = coordinator.begin(1, 1);
      final next = await coordinator.acquireBundleForDiagnostics(() => owner,
          ticket: ticket,
          currentLineageGeneration: () => 1,
          currentAuthenticationGeneration: () => 1,
          modeAllowed: () => true);
      expect(calls.last, '/api/authoritative-state');
      expect(baseline(next).toJson(), baseline(old).toJson());
      expect(next.envelope.revision, old.envelope.revision);
      expect(next.envelope.evaluationDate, old.envelope.evaluationDate);
    });
  }

  for (final race in ['newer-refresh', 'logout', 'relogin', 'mutation']) {
    test('late diagnostic bundle cannot authorize stale publication: $race',
        () async {
      final response = Completer<http.Response>();
      final api = MoneyNoteApiClient(
          baseUrl: 'http://synthetic.invalid',
          client: MockClient((_) => response.future));
      final c = CoherentRefreshCoordinator(api,
          localToday: () => '2026-10-05',
          formatDate: (d) => d.toIso8601String().substring(0, 10));
      var auth = 1;
      var lineage = 1;
      AuthUser? user = owner;
      final ticket = c.begin(lineage, auth);
      final pending = c.acquireBundleForDiagnostics(() => user,
          ticket: ticket,
          currentLineageGeneration: () => lineage,
          currentAuthenticationGeneration: () => auth,
          modeAllowed: () => true);
      final rejection = expectLater(
          pending,
          throwsA(isA<MoneyNoteApiException>()
              .having((e) => e.code, 'code', 'stale_authoritative_bundle')));
      if (race == 'newer-refresh') {
        c.begin(lineage, auth);
      }
      if (race == 'logout') {
        auth++;
        user = null;
        c.invalidateAuthentication();
      }
      if (race == 'relogin') {
        auth++;
      }
      if (race == 'mutation') {
        lineage++;
      }
      response.complete(
          http.Response.bytes(utf8.encode(jsonEncode(specimen())), 200));
      await rejection;
      expect(
          c.mayInstall(ticket,
              currentLineageGeneration: lineage,
              currentAuthenticationGeneration: auth,
              modeAllowed: true),
          false);
    });
  }
}
