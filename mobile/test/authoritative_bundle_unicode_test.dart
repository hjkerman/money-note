import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/authoritative_bundle_validation.dart';
import 'package:money_note_mobile/src/coherent_refresh_coordinator.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'authoritative_bundle_test.dart'
    show baseline, owner, parentAt, parseWire, reseal, specimen;

Iterable<List<Object>> stringPaths(Object? value,
    [List<Object> path = const []]) sync* {
  if (value is String) {
    yield path;
  } else if (value is Map) {
    for (final entry in value.entries) {
      yield* stringPaths(entry.value, [...path, entry.key as String]);
    }
  } else if (value is List) {
    for (var i = 0; i < value.length; i++) {
      yield* stringPaths(value[i], [...path, i]);
    }
  }
}

List<Map<String, dynamic>> unicodeCases() =>
    (jsonDecode(File('test/fixtures/bundle_unicode.json').readAsStringSync())
            as List)
        .cast<Map<String, dynamic>>();

String unicodeValue(Map c) =>
    String.fromCharCodes((c['units'] as List).cast<int>());

// All these surfaces accept the valid controls without a domain change.
Map<String, dynamic> unicodeWire(String surface, String value) {
  final w = specimen();
  final data = w['snapshot']['data'];
  if (surface == 'event-key' || surface == 'nullable-event-metadata') {
    final field =
        surface == 'event-key' ? 'idempotency_key' : 'request_fingerprint';
    final raw = data['card_payment_events'][0];
    raw[field] = value;
    for (final event in w['state']['card_payment_status']['events']) {
      if (event['id'] == raw['id']) event[field] = value;
    }
  } else if (surface == 'snapshot-label') {
    data['app_labels'].add({
      'key': 'unicode-test',
      'value': value,
      'updated_at': '2026-10-05 12:00:00'
    });
  } else if (surface == 'shared-title') {
    final entry = (w['state']['entries'] as List)
        .firstWhere((r) => r['entry_kind'] == 'expense');
    entry['title'] = value;
    (data['ledger_entries'] as List)
        .singleWhere((r) => r['id'] == entry['id'])['title'] = value;
    for (final row in w['state']['card_payment_status']['rows']) {
      if (row['is_group'] == false && row['id'] == entry['id']) {
        row['title'] = value;
      }
    }
  } else if (surface == 'projection-message') {
    w['state']['judgment']['budget']['message'] = value;
  } else if (surface == 'dynamic-key') {
    w['state']['judgment']['category_labels'][value] = 'Unicode control';
  } else {
    throw StateError(surface);
  }
  reseal(w);
  return w;
}

const surfaces = [
  'event-key',
  'nullable-event-metadata',
  'snapshot-label',
  'shared-title',
  'projection-message',
  'dynamic-key'
];

Iterable<(String, Map<String, dynamic>)> malformedUnicodeWires() sync* {
  for (final c in unicodeCases().where((c) => c['accept'] == false)) {
    final value = unicodeValue(c);
    for (final surface in surfaces) {
      yield ('${c['name']}/$surface', unicodeWire(surface, value));
    }
    for (final tree in [
      value,
      {
        'outer': [
          null,
          false,
          0,
          {'inner': value}
        ]
      },
      {
        'outer': [
          {
            'inner': {value: 'key control'}
          }
        ]
      }
    ]) {
      final w = specimen();
      w['state']['owner_discount_month']['projection_policy']['parameters']
          ['nested'] = tree;
      yield ('${c['name']}/generic', w);
    }
  }
  final original = specimen();
  for (final path in stringPaths(original)) {
    final w = jsonDecode(jsonEncode(original)) as Map<String, dynamic>;
    parentAt(w, path)[path.last] = String.fromCharCodes([97, 0xdbff, 98]);
    yield ('rich/${path.join('.')}', w);
  }
}

void main() {
  for (final name in ['lone-high-min', 'lone-low-min', 'high-ascii']) {
    test('original escaped surrogate witness rejects: $name', () {
      final c = unicodeCases().singleWhere((c) => c['name'] == name);
      expect(
          () => parseWire(unicodeWire('event-key', unicodeValue(c)))
              .toCoherentBundle(owner),
          throwsFormatException);
    });
  }
  test('Unicode scalar matrix across Snapshot/projection/nullable/map keys',
      () {
    for (final c in unicodeCases()) {
      for (final surface in surfaces) {
        final w = unicodeWire(surface, unicodeValue(c));
        final bytes = utf8.encode(jsonEncode(
            w)); // Invalid units are JSON escapes, not invalid UTF-8 bytes.
        final stages = <String>[];
        if (c['accept'] == true) {
          final accepted = AuthoritativeBundle.decode(bytes,
              onStage: (s, t) => stages.add(s));
          expect(accepted.wire, w);
          expect(
              accepted.wire['snapshot']['manifest'], w['snapshot']['manifest']);
          expect(accepted.wire['authority'], w['authority']);
          expect(() => accepted.toCoherentBundle(owner), returnsNormally);
        } else {
          expect(
              () => AuthoritativeBundle.decode(bytes,
                  onStage: (s, t) => stages.add(s)).toCoherentBundle(owner),
              throwsA(isA<FormatException>().having(
                  (e) => e.message, 'reason', contains('Unicode surrogate'))),
              reason: '${c['name']}/$surface');
          expect(stages, isNot(contains('presence_types')));
        }
      }
    }
  });

  test('generic JSON values and keys cannot bypass scalar validation', () {
    for (final c in unicodeCases()) {
      final value = unicodeValue(c);
      for (final tree in [
        value,
        {
          'outer': [
            null,
            false,
            0,
            {'inner': value}
          ]
        },
        {
          'outer': [
            {
              'inner': {value: 'key control'}
            }
          ]
        }
      ]) {
        final decoded = jsonDecode(jsonEncode(tree));
        if (c['accept'] == true) {
          validateBundleUnicode(tree);
          validateBundleUnicode(decoded);
          expect(jsonEncode(tree), jsonEncode(decoded));
        } else {
          expect(() => validateBundleUnicode(tree), throwsFormatException);
          expect(() => validateBundleUnicode(decoded), throwsFormatException);
          // Shape 'j' is permissive by design. The complete admission check
          // must precede policy compatibility even in nested generic data.
          final w = specimen();
          w['state']['owner_discount_month']['projection_policy']['parameters']
              ['nested'] = decoded;
          expect(
              () => parseWire(w),
              throwsA(isA<FormatException>().having(
                  (e) => e.message, 'reason', contains('Unicode surrogate'))));
        }
      }
    }
  });

  test('all isolated surrogate code units reject and valid pairs accept', () {
    for (var unit = 0xd800; unit <= 0xdfff; unit++) {
      expect(() => validateBundleUnicode(String.fromCharCode(unit)),
          throwsFormatException);
    }
    for (var high = 0xd800; high <= 0xdbff; high++) {
      validateBundleUnicode(String.fromCharCodes([high, 0xdc00]));
      validateBundleUnicode(String.fromCharCodes([high, 0xdfff]));
    }
    expect(
        unicodeValue(
            unicodeCases().singleWhere((c) => c['name'] == 'composed')),
        isNot(unicodeValue(
            unicodeCases().singleWhere((c) => c['name'] == 'combining'))));
  });

  test(
      'explicit JSON surrogate escapes preserve valid pairs, reject malformed units',
      () {
    for (final c in unicodeCases()) {
      final value = unicodeValue(c);
      final escaped =
          '"${(c['units'] as List).map((u) => '\\u${(u as int).toRadixString(16).padLeft(4, '0').toUpperCase()}').join()}"';
      expect((jsonDecode(escaped) as String).codeUnits, value.codeUnits);
      final text = jsonEncode(unicodeWire('event-key', value))
          .replaceAll(jsonEncode(value), escaped);
      if (c['accept'] == true) {
        expect(AuthoritativeBundle.decode(utf8.encode(text)).wire,
            unicodeWire('event-key', value));
      } else {
        expect(() => AuthoritativeBundle.decode(utf8.encode(text)),
            throwsFormatException);
      }
    }
  });

  test('invalid literal UTF-8 is still rejected before JSON admission', () {
    expect(() => AuthoritativeBundle.decode([0x22, 0xed, 0xa0, 0x80, 0x22]),
        throwsFormatException);
  });

  test(
      'every rich-bundle string rejects before shape/hash, not by stale hashes',
      () {
    final original = specimen();
    for (final path in stringPaths(original)) {
      final w = jsonDecode(jsonEncode(original)) as Map<String, dynamic>;
      parentAt(w, path)[path.last] = String.fromCharCodes([97, 0xdbff, 98]);
      expect(
          () => parseWire(w),
          throwsA(isA<FormatException>().having(
              (e) => e.message, 'reason', contains('Unicode surrogate'))),
          reason: path.join('.'));
    }
  });

  test('malformed strings block actual consumer publication in both stores',
      () async {
    for (final attack in malformedUnicodeWires()) {
      for (final existing in [false, true]) {
        final dir = await Directory.systemTemp.createTemp('mn-unicode-');
        try {
          final store = OfflineStore(directoryProvider: () async => dir);
          final file = File('${dir.path}/offline-mode/baseline.json');
          if (existing) {
            await store.replaceBaseline(
                baseline(parseWire(specimen()).toCoherentBundle(owner)));
          }
          final before = existing ? await file.readAsBytes() : null;
          final api = MoneyNoteApiClient(
              baseUrl: 'http://synthetic.invalid',
              client: MockClient((_) async => http.Response.bytes(
                  utf8.encode(jsonEncode(attack.$2)), 200)));
          final coordinator = CoherentRefreshCoordinator(api,
              localToday: () => '2026-10-05',
              formatDate: (d) => d.toIso8601String().substring(0, 10));
          final ticket = coordinator.begin(1, 1);
          var installed = false;
          Future<void> consume() async {
            final candidate = await coordinator.acquireBundleForDiagnostics(
                () => owner,
                ticket: ticket,
                currentLineageGeneration: () => 1,
                currentAuthenticationGeneration: () => 1,
                modeAllowed: () => true);
            await store.replaceBaseline(baseline(candidate), beforePublish: () {
              if (!coordinator.mayInstall(ticket,
                  currentLineageGeneration: 1,
                  currentAuthenticationGeneration: 1,
                  modeAllowed: true)) {
                throw StateError('stale');
              }
            });
            installed = true;
          }

          await expectLater(consume(), throwsA(isA<MoneyNoteApiException>()),
              reason: '${attack.$1}/$existing');
          expect(installed, false);
          if (existing) {
            expect(await file.readAsBytes(), before);
            expect(await store.loadBaseline(), isNotNull);
          } else {
            expect(await file.exists(), false);
            expect(await store.loadBaseline(), isNull);
          }
        } finally {
          await dir.delete(recursive: true);
        }
      }
    }
  }, timeout: const Timeout(Duration(minutes: 4)));

  test('valid Unicode survives actual durable serialization/readback unchanged',
      () async {
    final dir = await Directory.systemTemp.createTemp('mn-unicode-valid-');
    try {
      final store = OfflineStore(directoryProvider: () async => dir);
      for (final c in unicodeCases().where((c) => c['accept'] == true)) {
        for (final surface in surfaces) {
          final value = unicodeValue(c);
          final w = unicodeWire(surface, value);
          final accepted = baseline(parseWire(w).toCoherentBundle(owner));
          await store.replaceBaseline(accepted);
          expect((await store.loadBaseline())!.toJson(), accepted.toJson());
          if (surface == 'shared-title') {
            final raw = (await store.loadBaseline())!
                .authoritativeSnapshot!['data']['ledger_entries'] as List;
            expect(raw.any((r) => r['title'] == value), true,
                reason: c['name']);
          }
        }
      }
    } finally {
      await dir.delete(recursive: true);
    }
  });
}
