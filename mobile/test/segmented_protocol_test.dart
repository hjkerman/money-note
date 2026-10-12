import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';

import 'support/segmented_fixture.dart';

void main() {
  final golden = ServerGolden();
  final vectors = jsonDecode(
      File('../docs/specimens/t66c-canonical-vectors.json')
          .readAsStringSync()) as Map;
  for (final vector in vectors['valid']) {
    test('C1 independent scalar ${vector['id']}', () {
      final value = decodeC1(utf8.encode(vector['input_json'] as String),
          requireCanonical: false);
      final encoded = encodeC1(value);
      expect(utf8.decode(encoded), vector['expected_c1']);
      expect(encoded.length, vector['utf8_bytes']);
      expect(sha256.convert(encoded).toString(), vector['sha256_c1']);
    });
  }
  for (final vector in vectors['invalid']) {
    test('C1 rejects independent ${vector['id']}', () {
      expect(
          () => decodeC1(utf8.encode(vector['input_json'] as String),
              requireCanonical: false),
          throwsA(isA<SegmentedException>()));
    });
  }
  for (final raw in [
    '{"x":-1e-400}',
    '{"x":1000.00000000000001}',
    '{"x":1.5}',
    '{"x":1e309}',
    '{"x":9223372036854775808}',
    '{"x":1,"x":2}',
    '{"x":1,"\\u0078":2}',
    '{"x":-0}',
    '{"x":1e0}',
    '{"x":"\\u0061"}',
    '{"b":1,"a":2}',
    '{}\n',
    '{"x":NaN}'
  ]) {
    test('C1 rejects malformed $raw', () {
      expect(
          () => decodeC1(utf8.encode(raw)), throwsA(isA<SegmentedException>()));
    });
  }
  test('C1 int64 endpoints and REAL negative zero are exact', () {
    const raw =
        '[-9223372036854775808,9223372036854775807,9007199254740991.0,-0.0]';
    expect(utf8.decode(encodeC1(decodeC1(utf8.encode(raw)))), raw);
  });
  test('C1 UTF8 and nesting budgets fail closed', () {
    expect(() => decodeC1([0xff]), throwsA(isA<SegmentedException>()));
    expect(() => decodeC1(utf8.encode('${'[' * 130}0${']' * 130}')),
        throwsA(isA<SegmentedException>()));
    expect(
        () => objectHash('invented', []), throwsA(isA<SegmentedException>()));
    expect(() => TreeKey.parse(['t', '\ud800'], 'app_labels'),
        throwsA(isA<SegmentedException>()));
  });
  for (final object in golden.objects) {
    final kind = object['kind'] as String;
    test('actual server object golden $kind', () {
      final raw = golden.bytes(kind), ref = golden.ref(kind);
      // SHA framing calculated independently of the client hash helper.
      expect(
          sha256.convert([
            ...ascii.encode('money-note.sync.v1/$kind'),
            0,
            ...raw
          ]).toString(),
          ref.hash);
      final verified = VerifiedObject.verify(raw, ref, golden.cache);
      expect(verified.bytes, raw);
      expect(verified.kind, kind);
    });
  }
  test('server Target exact view identity and lease metadata', () {
    final target = golden.manifest.target.toJson()..remove('sync_root');
    expect(
        sha256.convert([
          ...ascii.encode('money-note.sync.v1/view'),
          0,
          ...encodeC1(target)
        ]).toString(),
        golden.manifest.target.syncRoot);
    expect(golden.manifest.leaseElapsedAt(golden.manifest.expiresAt), isTrue);
    expect(
        golden.manifest.leaseElapsedAt(
            golden.manifest.expiresAt.subtract(const Duration(seconds: 1))),
        isFalse);
  });
  test('release artifacts exact bytes and hashes match client allow-list', () {
    expect(
        File('assets/segmented/isolated-release-artifacts.json')
            .readAsBytesSync(),
        File('../docs/specimens/t66d3b-release-artifacts.json')
            .readAsBytesSync());
    final artifact = jsonDecode(
        File('../docs/specimens/t66d3b-release-artifacts.json')
            .readAsStringSync()) as Map;
    final hashes = {
      'raw_schema': ReleaseContract.rawSchema,
      'projection_schema': ReleaseContract.projectionSchema,
      'policy_registry': ReleaseContract.policyRegistry,
      'financial_engine': ReleaseContract.financialEngine
    };
    for (final e in hashes.entries) {
      final a = artifact['artifacts'][e.key];
      final raw = base64Decode(a['data_base64'] as String);
      expect('${raw.length}', a['bytes']);
      expect(sha256.convert(raw).toString(), e.value);
      expect(a['sha256'], e.value);
    }
  });
  for (final field in golden.manifest.target.versions.toJson().keys) {
    test('unknown version field $field rejected', () {
      final changed = targetChanged(golden, (v) {
        v['versions'][field] = v['versions'][field] is int ? 99 : '0' * 64;
      });
      expect(
          () => SyncTarget.parse(changed), throwsA(isA<SegmentedException>()));
    });
  }
  test('principal epoch origin namespace not interchangeable', () {
    final original = golden.cache;
    for (final change in <void Function(Map<String, dynamic>)>[
      (v) => v['principal_id'] = 2,
      (v) => v['ns']['epoch'] = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    ]) {
      final target = SyncTarget.parse(targetChanged(golden, change));
      expect(CacheNamespace.forTarget(original.origin, target).key,
          isNot(original.key));
      expect(() => original.verifyTarget(target),
          throwsA(isA<SegmentedException>()));
    }
    expect(
        CacheNamespace.forTarget(
                'https://another.invalid', golden.manifest.target)
            .key,
        isNot(original.key));
    expect(
        () => CacheNamespace.forTarget(
            'http://synthetic.invalid', golden.manifest.target),
        throwsA(isA<SegmentedException>()));
  });
  test('invalid evaluation and malformed manifest rejected', () {
    final target = golden.manifest.target.toJson();
    target['context']['evaluation_date'] = '2026-02-30';
    expect(() => SyncTarget.parse(target), throwsA(isA<SegmentedException>()));
    final raw = decodeC1(golden.manifest.bytes) as Map<String, dynamic>;
    raw['expires_at'] = raw['validated_at'];
    expect(() => ObservationManifest.fromBytes(encodeC1(raw)),
        throwsA(isA<SegmentedException>()));
    raw['unknown'] = true;
    expect(() => ObservationManifest.fromBytes(encodeC1(raw)),
        throwsA(isA<SegmentedException>()));
  });
  test('strict chunk bytes and bounds, not transport/assembly', () {
    final raw = golden.bytes('raw-root'), ref = golden.ref('raw-root');
    final wire = <String, dynamic>{
      'ref': ref.toJson(),
      'offset': '0',
      'length': raw.length,
      'data_base64': base64Encode(raw)
    };
    expect(ObjectChunk.parse(wire).bytes, raw);
    for (final change in <void Function(Map<String, dynamic>)>[
      (v) => v['length'] = 0,
      (v) => v['offset'] = '-1',
      (v) => v['data_base64'] = '${v['data_base64']}\n',
      (v) => v['offset'] = ref.bytes,
    ]) {
      final changed = Map<String, dynamic>.from(wire);
      change(changed);
      expect(
          () => ObjectChunk.parse(changed), throwsA(isA<SegmentedException>()));
    }
  });
  test('bytes ownership and Unicode/money strings never normalized', () {
    final obj = VerifiedObject.verify(golden.bytes('snapshot-leaf'),
        golden.ref('snapshot-leaf'), golden.cache);
    expect((obj.body['rows'] as List).single['value']['title'],
        contains('한글 😀 e\u0301'));
    final copy = obj.bytes;
    copy[0] = 0;
    expect(obj.bytes[0], 123);
    final body = golden.body('snapshot-leaf');
    body['table'] = 'app_settings';
    body['min'] = ['t', 'scheduled_income'];
    body['max'] = body['min'];
    body['rows'] = [
      {
        'key': body['min'],
        'value': {
          'key': 'scheduled_income',
          'value': ' +0001000.00 ',
          'updated_at': 'synthetic'
        }
      }
    ];
    final raw = encodeC1(body);
    final setting =
        VerifiedObject.verify(raw, refFor('snapshot-leaf', raw), golden.cache);
    expect(setting.body['rows'][0]['value']['value'], ' +0001000.00 ');
  });
  test('internal proof/wrong kind/context/version/hash rejected', () {
    for (final field in ['kind', 'canon', 'raw_schema', 'ns']) {
      final body = golden.body('snapshot-leaf');
      switch (field) {
        case 'kind':
          body[field] = 'input-proof';
        case 'canon':
          body[field] = 2;
        case 'raw_schema':
          body[field] = '0' * 64;
        case 'ns':
          body['ns']['epoch'] = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
      }
      final raw = encodeC1(body);
      final ref = ObjectRef.parse({'hash': '0' * 64, 'bytes': '${raw.length}'});
      expect(() => VerifiedObject.verify(raw, ref, golden.cache),
          throwsA(isA<SegmentedException>()));
    }
    final raw = golden.bytes('raw-root');
    expect(
        () => VerifiedObject.verify(
            raw.sublist(1), golden.ref('raw-root'), golden.cache),
        throwsA(isA<SegmentedException>()));
  });
  for (final edit in [
    'canon',
    'raw_schema',
    'ns',
    'table',
    'count',
    'key',
    'unknown'
  ]) {
    test('hash-valid malformed object $edit rejected by format/context checks',
        () {
      final body = golden.body('snapshot-leaf');
      switch (edit) {
        case 'canon':
          body['canon'] = 2;
        case 'raw_schema':
          body['raw_schema'] = '0' * 64;
        case 'ns':
          body['ns']['epoch'] = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
        case 'table':
          body['table'] = 'unknown';
        case 'count':
          body['count'] = '2';
        case 'key':
          body['rows'][0]['key'] = ['i', '-0'];
        case 'unknown':
          body['extra'] = true;
      }
      final raw = encodeC1(body);
      expect(
          () => VerifiedObject.verify(
              raw, refFor('snapshot-leaf', raw), golden.cache),
          throwsA(isA<SegmentedException>()));
    });
  }
  test(
      'hot is checked as twelve typed projections without financial recalculation',
      () {
    final body = golden.body('hot');
    body['state'].remove('summary');
    final raw = encodeC1(body);
    expect(() => VerifiedObject.verify(raw, refFor('hot', raw), golden.cache),
        throwsA(isA<SegmentedException>()));
    body['state'] = golden.body('hot')['state'];
    body['context']['financial_engine'] = '0' * 64;
    final other = encodeC1(body);
    expect(
        () => VerifiedObject.verify(other, refFor('hot', other), golden.cache),
        throwsA(isA<SegmentedException>()));
  });
}
