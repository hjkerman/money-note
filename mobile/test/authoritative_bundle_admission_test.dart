import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/authoritative_bundle_contract.dart';
import 'package:money_note_mobile/src/authoritative_bundle_validation.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'authoritative_bundle_test.dart'
    show baseline, owner, parseWire, reseal, specimen;

Map<String, dynamic> attack(void Function(Map<String, dynamic>) mutate) {
  final wire = specimen();
  mutate(wire);
  reseal(wire); // Reach semantic admission, not merely stale-hash rejection.
  return wire;
}

final exactAttacks = <String, void Function(Map<String, dynamic>)>{
  'M1 unsupported book_section': (w) {
    final row = w['snapshot']['data']['ledger_entries'][0];
    row['book_section'] = 'CORRUPT';
    for (final p in w['state']['entries']) {
      if (p['id'] == row['id']) p['book_section'] = 'CORRUPT';
    }
  },
  'M1 unsupported payment event_type': (w) {
    final row = w['snapshot']['data']['card_payment_events'][0];
    row['event_type'] = 'CORRUPT';
    for (final p in w['state']['card_payment_status']['events']) {
      if (p['id'] == row['id']) p['event_type'] = 'CORRUPT';
    }
  },
  'M2 duplicate projected entry ID': (w) {
    w['state']['entries']
        .add(Map<String, dynamic>.from(w['state']['entries'][0]));
  },
  'M2 duplicate confirmed source ID': (w) {
    w['state']['confirmed_planned_entries'].add(
        Map<String, dynamic>.from(w['state']['confirmed_planned_entries'][0]));
  },
  'M3 contradictory same-ID policy rate': (w) {
    w['snapshot']['card_charge_policy']['cards']['owner'][0]['parameters']
        ['rate'] = '0.02';
  },
};

void main() {
  test(
      'shared finite domains accept every supported value and reject corrupt types',
      () {
    for (final domain in bundleFiniteDomains.entries) {
      for (final value in domain.value) {
        expect(() => validateBundleShape(value, 'v:${domain.key}'),
            returnsNormally);
      }
      for (final value in <Object?>['CORRUPT', '', null, false, 0, [], {}]) {
        expect(() => validateBundleShape(value, 'v:${domain.key}'),
            throwsFormatException);
      }
    }
  });
  for (final entry in exactAttacks.entries) {
    test(entry.key, () {
      expect(() => parseWire(attack(entry.value)).toCoherentBundle(owner),
          throwsFormatException);
    });
  }

  test('M1 sibling notification target obeys the existing DB CHECK domain', () {
    final wire = attack((w) {
      w['snapshot']['data']['notification_candidate_registrations'].add({
        'registration_key': 'synthetic-admission',
        'target': 'CORRUPT',
        'target_id': 1,
        'request_fingerprint': 'synthetic',
        'created_at': '2026-10-05 00:00:00',
      });
    });
    expect(() => parseWire(wire), throwsFormatException);
  });

  for (final path in <List<String>>[
    ['panels'],
    ['cash_flows'],
    ['card_payment_status', 'rows'],
    ['card_payment_status', 'events'],
  ]) {
    test('M2 sibling unique projection identity ${path.join('.')}', () {
      final wire = attack((w) {
        dynamic collection = w['state'];
        for (final key in path) {
          collection = collection[key];
        }
        collection.add(Map<String, dynamic>.from(collection[0]));
      });
      expect(() => parseWire(wire), throwsFormatException);
    });
  }

  for (final change in <String, void Function(Map)>{
    'definition kind': (p) {
      p['type'] = 'no_automatic_discount';
      p['parameters'] = {};
    },
    'extra semantic parameter': (p) {
      p['parameters']['threshold'] = 100;
    },
    'rounding': (p) {
      p['rounding'] = 'none';
    },
    'scope identity': (p) {
      p['policy_id'] = 'family-flat-statement-1.2';
    },
    'noncanonical rate text': (p) {
      p['parameters']['rate'] = '0.0120';
    },
  }.entries) {
    test('M3 sibling ${change.key}', () {
      final wire = attack((w) {
        change.value(w['state']['owner_discount_month']['projection_policy']);
      });
      expect(() => parseWire(wire), throwsFormatException);
    });
  }

  test('M3 repeated definition across timeline/selector must agree', () {
    final wire = attack((w) {
      w['snapshot']['card_charge_policy']['profile_selectors']['transit']
          ['none_mode']['policy']['parameters']['threshold'] = 100;
    });
    expect(() => parseWire(wire), throwsFormatException);
  });

  test('same-ID agreement cannot legitimize an unsupported policy kind', () {
    final wire = attack((w) {
      w['snapshot']['card_charge_policy']['cards']['owner'][0]['type'] =
          'CORRUPT';
      w['state']['owner_discount_month']['projection_policy']['type'] =
          'CORRUPT';
      w['state']['owner_discount_month']['projection_policy']['rounding'] =
          'none';
    });
    expect(() => parseWire(wire), throwsFormatException);
  });

  test(
      'unregistered policy binding is not made canonical by identical witnesses',
      () {
    final wire = attack((w) {
      final bindings =
          w['snapshot']['card_charge_policy']['cards']['owner'] as List;
      bindings.add({
        ...Map<String, dynamic>.from(bindings.first),
        'effective_from': '2026-09'
      });
    });
    expect(() => parseWire(wire), throwsFormatException);
  });

  test('policy binding identity is scope + effective month, not definition',
      () {
    for (final scope in ['owner', 'family', 'toll', 'transit']) {
      final wire = attack((w) {
        final bindings =
            w['snapshot']['card_charge_policy']['cards'][scope] as List;
        bindings.add(Map<String, dynamic>.from(bindings.first));
      });
      expect(() => parseWire(wire), throwsFormatException, reason: scope);
    }
  });

  test(
      'parameter map ordering is irrelevant, but canonical string text is not normalized',
      () {
    final wire = attack((w) {
      w['snapshot']['card_charge_policy']['cards']['owner'][0]
          ['parameters'] = {'rate': '0.012'};
    });
    expect(() => parseWire(wire), returnsNormally);
    wire['state']['owner_discount_month']['projection_policy']['parameters']
        ['rate'] = '0.0120';
    expect(() => parseWire(wire), throwsFormatException);
  });

  test(
      'collection duplicates reject at first/middle/last with conflicting content',
      () {
    for (final name in [
      'entries',
      'confirmed_planned_entries',
      'panels',
      'cash_flows'
    ]) {
      for (final placement in ['first', 'middle', 'last']) {
        for (final conflicting in [false, true]) {
          final wire = attack((w) {
            final rows = w['state'][name] as List;
            final extra = Map<String, dynamic>.from(rows.first);
            if (conflicting) extra['title'] = 'Different mutable description';
            final index = placement == 'first'
                ? 0
                : placement == 'last'
                    ? rows.length
                    : rows.length ~/ 2;
            rows.insert(index, extra);
          });
          expect(() => parseWire(wire), throwsFormatException,
              reason: '$name/$placement/$conflicting');
        }
      }
    }
  });

  test('close-item identity is kind + ID, never title or ID across namespaces',
      () {
    // Generated by the canonical backend with fixed panel 11 and planned
    // ledger source 11. The former fabricated control had no such sources.
    final wire = jsonDecode(
        File('test/fixtures/authoritative_bundle/identity_edges.json')
            .readAsStringSync()) as Map<String, dynamic>;
    expect(() => parseWire(wire), returnsNormally);
    wire['state']['month_close_status']['unconfirmed_recurring_items'].add(
        Map<String, dynamic>.from(wire['state']['month_close_status']
            ['unconfirmed_recurring_items'][0]));
    expect(() => parseWire(wire), throwsFormatException);
  });

  test('two different payment rows cannot claim the same financial member', () {
    final wire = specimen();
    final rows = wire['state']['card_payment_status']['rows'] as List;
    final extra = Map<String, dynamic>.from(rows.first);
    extra['id'] = -99999;
    extra['is_group'] = true;
    rows.add(extra);
    expect(() => parseWire(wire), throwsFormatException);
  });

  test('payment group and raw entry IDs have distinct canonical namespaces',
      () {
    // The backend groups toll rows under -firstEntryId, while SQLite permits
    // negative raw entry IDs. Group identity must not collide with a raw row.
    final wire = attack((w) {
      final raw = (w['snapshot']['data']['ledger_entries'] as List)
          .singleWhere((r) => r['payment_key'] == 'old-card');
      final previous = raw['id'];
      final group = (w['state']['card_payment_status']['rows'] as List)
          .singleWhere((r) => r['is_group'] == true);
      raw['id'] = group['id'];
      for (final item in w['snapshot']['data']['card_payment_batch_items']) {
        if (item['entry_id'] == previous) item['entry_id'] = raw['id'];
      }
      final projected = (w['state']['card_payment_status']['rows'] as List)
          .singleWhere((r) => r['payment_key'] == 'old-card');
      projected['id'] = raw['id'];
      projected['entry_ids'] = [raw['id']];
      projected['payment_parts'][0]['entry_id'] = raw['id'];
    });
    expect(() => parseWire(wire), returnsNormally);
    wire['state']['card_payment_status']['rows'].add(Map<String, dynamic>.from(
        wire['state']['card_payment_status']['rows'][0]));
    expect(() => parseWire(wire), throwsFormatException);
  });

  test('malformed semantic bundles cannot replace a durable valid baseline',
      () async {
    final directory = await Directory.systemTemp.createTemp('mn-admission-');
    addTearDown(() => directory.delete(recursive: true));
    final store = OfflineStore(directoryProvider: () async => directory);
    final original = baseline(parseWire(specimen()).toCoherentBundle(owner));
    await store.replaceBaseline(original);
    final file = (await directory
            .list(recursive: true)
            .where((entry) =>
                entry is File && entry.path.endsWith('/baseline.json'))
            .toList())
        .single as File;
    final bytes = await file.readAsBytes();
    for (final entry in exactAttacks.entries) {
      final wire = attack(entry.value);
      await expectLater(() async {
        final bundle =
            AuthoritativeBundle.decode(utf8.encode(jsonEncode(wire)));
        await store.replaceBaseline(baseline(bundle.toCoherentBundle(owner)));
      }(), throwsFormatException, reason: entry.key);
      expect((await store.loadBaseline())!.toJson(), original.toJson());
      expect(await file.readAsBytes(), bytes);
    }
    final emptyDirectory =
        await Directory.systemTemp.createTemp('mn-admission-empty-');
    addTearDown(() => emptyDirectory.delete(recursive: true));
    final emptyStore =
        OfflineStore(directoryProvider: () async => emptyDirectory);
    for (final entry in exactAttacks.entries) {
      await expectLater(() async {
        final bundle = parseWire(attack(entry.value)).toCoherentBundle(owner);
        await emptyStore.replaceBaseline(baseline(bundle));
      }(), throwsFormatException);
      expect(await emptyStore.loadBaseline(), isNull);
    }
  });
}
