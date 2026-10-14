@Timeout(Duration(minutes: 5))
library;

import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/authoritative_bundle_validation.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_projection.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';

import 'support/offline_mode_fixtures.dart';
import 'support/segmented_fixture.dart';

const _baselineCommit = 'ab59d6bbc39f27c36beb059f984ef527ac7b0bef';
const _settings = [
  'scheduled_income',
  'cash_flow_balance',
  'card_limit',
  'base_next_month_liquidity',
  'liquidity_status'
];

bool _accepts(void Function() action) {
  try {
    action();
    return true;
  } on FormatException {
    return false;
  }
}

Map<String, dynamic> _baselineWire(Map<String, dynamic> wire) => {
      ...wire['state'] as Map<String, dynamic>,
      'schema_version': 4,
      'synced_at': wire['snapshot']['exported_at'],
      'user': baselineFixture().toJson()['user'],
      'authoritative_snapshot': wire['snapshot'],
      'server_state_fingerprint': wire['authority']['state_fingerprint'],
      'resolved_reconciliation_id': null,
      'discount_policy_defaults': wire['authority']['discount_policy_defaults'],
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final golden = ServerGolden();
  final reported = jsonDecode(
          File('test/fixtures/segmented_money_vectors.json').readAsStringSync())
      as Map;
  late Directory temporary;
  late Map<String, dynamic> evidence;
  late List<dynamic> corpus, originalInputAcceptance;
  late String repository;
  setUpAll(() async {
    temporary = Directory.systemTemp.createTempSync('money-note-e4-p0-');
    repository = Directory.current.parent.path;
    final fixture = await Process.run('$repository/.venv/bin/python',
        ['$repository/docs/benchmarks/t66e4-contract/probe.py']);
    expect(fixture.exitCode, 0, reason: fixture.stderr as String);
    evidence = jsonDecode(fixture.stdout as String) as Map<String, dynamic>;
    final corpusFile = File('${temporary.path}/server-corpus.json');
    final generated = await Process.run('$repository/.venv/bin/python', [
      '$repository/docs/benchmarks/t66e1-a01-a02-reaudit/make_corpus.py',
      corpusFile.path
    ]);
    expect(generated.exitCode, 0, reason: generated.stderr as String);
    corpus =
        (jsonDecode(corpusFile.readAsStringSync()) as Map)['cases'] as List;
    expect(corpus.length, 4755);
    // Exact archived Git source, SHA compared with the actual baseline before
    // the correction. No Git history/network prerequisite in a shallow CI clone.
    final old =
        File('test/fixtures/money_before_e4_p0.dart.txt').readAsStringSync();
    expect(sha256.convert(utf8.encode(old)).toString(),
        '9f1aef7d287f6c9c321f8d4e2fb5b9a33b4f62df9a1270820aed2a814889a02e',
        reason: 'actual $_baselineCommit money.dart oracle');
    expect(
        File('lib/src/money.dart').readAsStringSync().startsWith(old), isTrue,
        reason:
            'frozen exactMoney/validateMoneyPayload source must stay byte-identical');
    final driver = File('${temporary.path}/original_input.dart');
    driver.writeAsStringSync("import 'dart:io';\nimport 'dart:convert';\n$old\n"
        r'''
void main() {
  final values = jsonDecode(stdin.readLineSync()!) as List;
  stdout.write(jsonEncode(values.map((v) {
    try { exactMoney(v); return true; } on FormatException { return false; }
  }).toList()));
}
''');
    final child = await Process.start('dart', [driver.path]);
    final output = child.stdout.transform(utf8.decoder).join();
    final errors = child.stderr.transform(utf8.decoder).join();
    child.stdin.writeln(jsonEncode(corpus.map((v) => v['value']).toList()));
    await child.stdin.close();
    expect(await child.exitCode, 0, reason: await errors);
    originalInputAcceptance = jsonDecode(await output) as List;
    expect(originalInputAcceptance.length, corpus.length);
  });
  tearDownAll(() => temporary.deleteSync(recursive: true));

  for (final raw in reported['vectors']) {
    final v = raw as Map;
    test('E4-P0 server-derived admission ${v['id']}', () {
      final text = v['value'] as String;
      final expected = v['accepted'] as bool;
      final before = text.codeUnits.toList();
      for (final key in _settings) {
        final settings = <String, dynamic>{key: text};
        final row = {'key': key, 'value': text, 'updated_at': '한글 😀 e\u0301'};
        final envelope = {
          'state': {'settings': settings},
          'snapshot': {
            'data': {
              'app_settings': [row]
            }
          }
        };
        expect(_accepts(() => exactAuthoritativeSettingMoney(text)), expected);
        expect(_accepts(() => validateAuthoritativeSettingsMoney(settings)),
            expected);
        expect(_accepts(() => validateAuthoritativeMoneyPayload(envelope)),
            expected);
        expect(_accepts(() => AppSettings.fromJson(settings)), expected);
        if (expected) expect(AppSettings.fromJson(settings).values[key], text);
        expect(settings[key], text);
        expect(row['value'], text);
      }
      expect(text.codeUnits, before);
    });
  }

  test(
      'independent 4755 server corpus: authoritative amount, E1 bytes and hash',
      () {
    for (final raw in corpus) {
      final v = raw as Map;
      final text = v['value'] as String;
      expect(
          _accepts(() => exactAuthoritativeSettingMoney(text)), v['accepted'],
          reason: v['id']);
      if (v['accepted'] == true) {
        expect(exactAuthoritativeSettingMoney(text), v['amount'],
            reason: v['id']);
        final bytes = base64Decode(v['data_base64'] as String);
        final object = VerifiedObject.verify(
            bytes, ObjectRef.parse(v['ref']), golden.cache);
        expect(object.bytes, bytes);
        expect(objectHash('snapshot-leaf', object.bytes), v['ref']['hash']);
        expect(object.body['rows'][0]['value']['value'], text);
      } else {
        expect(
            () => VerifiedObject.verify(base64Decode(v['data_base64']),
                ObjectRef.parse(v['ref']), golden.cache),
            throwsA(isA<SegmentedException>()));
      }
    }
  });

  test(
      'all 4755 frozen input and journal outcomes equal the committed old parser',
      () {
    for (var i = 0; i < corpus.length; i++) {
      final v = corpus[i] as Map, text = v['value'] as String;
      final expected = originalInputAcceptance[i];
      expect(_accepts(() => exactMoney(text)), expected, reason: v['id']);
      expect(_accepts(() => validateMoneyPayload({'amount_value': text})),
          expected,
          reason: v['id']);
      expect(
          _accepts(() => OfflineJournalOperation.fromJson({
                'schema_version': 1,
                'operation_id': 'p0-input-$i',
                'operation_type': 'CREATE_CASH_FLOW',
                'payload': {'amount_value': text},
                'created_at': '2026-10-05T00:00:00Z',
                'sequence': i + 1,
                'status': 'pending'
              })),
          expected,
          reason: v['id']);
    }
  });

  test(
      'numeric projections and non-setting money do not gain compatibility coercion',
      () {
    const text = '\u001c1000\u001f';
    for (final value in [
      {'amount_value': text},
      {
        'summary': {'cash_flow_balance': text}
      },
      {
        'settings': {'amount_value': text}
      },
      {
        'app_settings': [
          {'key': 'ordinary', 'value': 'x', 'amount_value': text}
        ]
      },
      {
        'settings': {'key': 'cash_flow_balance', 'value': text}
      },
    ]) {
      expect(() => validateAuthoritativeMoneyPayload(value),
          throwsFormatException);
    }
    for (final value in [
      maxMoney + 1,
      0.5,
      -0.5,
      double.infinity,
      double.nan,
      true
    ]) {
      expect(() => validateAuthoritativeMoneyPayload({'amount_value': value}),
          throwsFormatException);
    }
  });

  test(
      'original complete backend bundle and OfflineBaseline now pass unchanged',
      () {
    final wire = evidence['wire'] as Map<String, dynamic>;
    final raw = utf8.encode(jsonEncode(wire));
    final bundle = AuthoritativeBundle.decode(raw)
        .toCoherentBundle(baselineFixture().user);
    final baseline = OfflineBaseline.fromJson(_baselineWire(wire));
    const text = '\u001c+0001000.00\u001f';
    expect(bundle.candidate.settings.values['cash_flow_balance'], text);
    expect(baseline.settings.values['cash_flow_balance'], text);
    expect(baseline.authoritativeSnapshot, wire['snapshot']);
    expect(baseline.serverStateFingerprint,
        wire['authority']['state_fingerprint']);
    expect(bundle.envelope.fingerprint, baseline.serverStateFingerprint);
    expect(bundle.envelope.fingerprint,
        isNot(evidence['fixture']['manifest']['target']['sync_root']));
    expect(
        bundleHash({
          'schema_version': 7,
          'range': wire['snapshot']['range'],
          'card_charge_policy': wire['snapshot']['card_charge_policy'],
          'data': wire['snapshot']['data']
        }),
        wire['authority']['state_fingerprint']);
    expect(utf8.encode(jsonEncode(wire)), raw);
  });

  for (final invalid in [
    '\ufeff1000',
    '1000\ufeff',
    '10\ufeff00',
    '1e3',
    '1_000',
    '9007199254740992'
  ]) {
    test(
        'complete authoritative boundary rejects invalid setting ${jsonEncode(invalid)}',
        () {
      final wire =
          jsonDecode(jsonEncode(evidence['wire'])) as Map<String, dynamic>;
      wire['state']['settings']['cash_flow_balance'] = invalid;
      expect(() => AuthoritativeBundle.decode(utf8.encode(jsonEncode(wire))),
          throwsFormatException);
      final baseline = _baselineWire(wire);
      expect(() => OfflineBaseline.fromJson(baseline), throwsFormatException);
    });
  }

  test(
      'baseline durable publication/reopen preserves raw values, fingerprint and lineage',
      () async {
    final root = Directory('${temporary.path}/baseline')..createSync();
    final baseline = OfflineBaseline.fromJson(_baselineWire(evidence['wire']));
    final store = OfflineStore(directoryProvider: () async => root);
    final original = baseline.toJson(),
        fingerprint = store.recoveryLineageFingerprint(baseline);
    var guards = 0;
    await store.replaceBaseline(baseline, beforePublish: () {
      guards++;
    });
    expect(guards, 1);
    final file = File('${root.path}/offline-mode/baseline.json');
    final committed = file.readAsBytesSync();
    expect(jsonDecode(utf8.decode(committed)), original);
    final reopened = OfflineStore(directoryProvider: () async => root);
    final recovered = (await reopened.loadBaseline())!;
    expect(recovered.toJson(), original);
    expect(reopened.recoveryLineageFingerprint(recovered), fingerprint);
    final process = await Process.start('$repository/.venv/bin/python', [
      '-c',
      'import json,sys,hashlib; b=json.load(sys.stdin); print(hashlib.sha256(json.dumps({"schema_version":1,"origin":"mobile-baseline-lineage","baseline":b},ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
    ]);
    final output = process.stdout.transform(utf8.decoder).join();
    final error = process.stderr.transform(utf8.decoder).join();
    process.stdin.writeln(jsonEncode(original));
    await process.stdin.close();
    expect(await process.exitCode, 0, reason: await error);
    expect((await output).trim(), fingerprint);
    await expectLater(
        store.replaceBaseline(baselineFixture(), beforePublish: () {
          throw StateError('synthetic authority invalidation');
        }),
        throwsStateError);
    expect(file.readAsBytesSync(), committed);
  });

  test('actual J append/reopen and pending marker bytes are unchanged',
      () async {
    final root = Directory('${temporary.path}/journal')..createSync();
    final store = OfflineStore(directoryProvider: () async => root);
    await store.replaceBaseline(baselineFixture());
    final marker = await store.beginOnlineWrite(1);
    final pending = File('${root.path}/offline-mode/online-write-1.json');
    final pendingBytes = pending.readAsBytesSync();
    var sequence = 0;
    for (final raw in evidence['vectors']) {
      final text = raw['value'] as String;
      final expected = _accepts(() => exactMoney(text));
      final journal = File('${root.path}/offline-mode/journal.ndjson');
      final before = journal.existsSync() ? journal.readAsBytesSync() : <int>[];
      final operation = store.appendOperation(
          type: OfflineOperationType.createCashFlow,
          payload: {
            'occurred_on': '2026-09-17',
            'title': '합성 한글 😀 e\u0301',
            'amount_value': text,
            'is_primary_income': 0
          },
          baseline: baselineFixture());
      if (!expected) {
        await expectLater(operation, throwsFormatException);
        expect(
            journal.existsSync() ? journal.readAsBytesSync() : <int>[], before);
      } else {
        final written = await operation;
        sequence++;
        expect(written.sequence, sequence);
        expect(written.payload['amount_value'], text);
        final rows = await OfflineStore(directoryProvider: () async => root)
            .loadJournal();
        expect(rows.last.operationId, written.operationId);
        expect(rows.last.payload['amount_value'], text);
        expect(
            rows.map((r) => r.sequence), List.generate(sequence, (i) => i + 1));
        expect(
            OfflineProjection.from(baselineFixture(), rows)
                .cashFlows
                .last
                .isOfflinePending,
            isTrue);
      }
      expect(pending.readAsBytesSync(), pendingBytes);
      expect((await store.loadPendingOnlineWrite(1))!.token, marker.token);
    }
  });

  test(
      'recovery artifact validates B compatibly but J with the original admission',
      () async {
    final root = Directory('${temporary.path}/artifact')..createSync();
    final store = OfflineStore(directoryProvider: () async => root);
    final baseline = OfflineBaseline.fromJson(_baselineWire(evidence['wire']));
    const metadata = OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
        reconciliationId: 'synthetic-p0-reconciliation',
        reconciliationChoice: ReconciliationChoice.applyToServer,
        phase: ReconciliationPhase.preparing);
    final op = OfflineJournalOperation(
        operationId: 'synthetic-p0-input',
        type: OfflineOperationType.createCashFlow,
        payload: {'amount_value': '1000'},
        createdAt: DateTime.utc(2026, 10, 5),
        sequence: 1);
    final artifact = await store.createMobileRecoveryArtifact(
        baseline: baseline, operations: [op], metadata: metadata);
    final content = jsonDecode(
        File('${root.path}/offline-mode/recovery/${artifact.filename}')
            .readAsStringSync()) as Map;
    expect(content['baseline'], baseline.toJson());
    expect(content['ordered_journal'], [op.toJson()]);
    expect(
        await store.verifyMobileRecoveryArtifact(artifact.filename,
            expectedBaseline: baseline, expectedOperations: [op]),
        artifact.sha256);
    final bad = OfflineJournalOperation(
        operationId: 'synthetic-bad-input',
        type: OfflineOperationType.createCashFlow,
        payload: {
          'settings': {'cash_flow_balance': '\u001c1000\u001f'}
        },
        createdAt: DateTime.utc(2026, 10, 5),
        sequence: 2);
    await expectLater(
        store.createMobileRecoveryArtifact(
            baseline: baseline, operations: [bad], metadata: metadata),
        throwsFormatException);
    expect((await store.listMobileRecoveryArtifacts()).length, 1);
  });

  test(
      'settings GET/PATCH response and baseline GET use the read boundary only',
      () async {
    final requests = <http.Request>[];
    final wire = evidence['wire'] as Map<String, dynamic>;
    final client = MockClient((request) async {
      requests.add(request);
      return http.Response(
          jsonEncode(request.url.path.contains('/settings')
              ? wire['state']['settings']
              : {
                  'snapshot': wire['snapshot'],
                  ...wire['authority'] as Map<String, dynamic>
                }),
          200,
          headers: {'content-type': 'application/json'});
    });
    final api =
        MoneyNoteApiClient(client: client, baseUrl: 'https://p0.synthetic');
    expect((await api.settings()).values['cash_flow_balance'],
        '\u001c+0001000.00\u001f');
    expect(
        (await api.updateSetting('owner_card_last4', '1234'))
            .values['cash_flow_balance'],
        '\u001c+0001000.00\u001f');
    expect(jsonDecode(requests.last.body), {'value': '1234'});
    expect((await api.offlineReconciliationBaseline())['snapshot'],
        wire['snapshot']);
    client.close();
  });

  test('API authoritative invalid BOM and non-setting money remain rejected',
      () async {
    final client = MockClient((_) async => http.Response(
        jsonEncode({'cash_flow_balance': '\ufeff1000'}), 200,
        headers: {'content-type': 'application/json; charset=utf-8'}));
    final api =
        MoneyNoteApiClient(client: client, baseUrl: 'https://p0.synthetic');
    await expectLater(api.settings(), throwsFormatException);
    client.close();
  });

  test(
      'existing MW wrapper preserves compatible B and original ordered J bytes',
      () async {
    final wire = evidence['wire'] as Map<String, dynamic>;
    final operations = [
      {
        'operation_id': 'synthetic-p0-ordered-1',
        'sequence': 1,
        'payload': {'amount_value': '+0001000.00'}
      },
      {
        'operation_id': 'synthetic-p0-ordered-2',
        'sequence': 2,
        'payload': {'amount_value': -1000}
      },
    ];
    final requests = <http.Request>[];
    final client = MockClient((request) async {
      requests.add(request);
      return http.Response('{}', 200);
    });
    final api =
        MoneyNoteApiClient(client: client, baseUrl: 'https://p0.synthetic');
    await api.reconcileOfflineMobileWins(
        reconciliationId: 'synthetic-p0-existing-mw',
        baselineFingerprint: wire['authority']['state_fingerprint'],
        baselineSnapshot: wire['snapshot'],
        operations: operations,
        mobileArtifactSha256: 'a' * 64,
        expectedServerFingerprint: 'b' * 64,
        confirmServerChanged: false,
        password: 'synthetic-not-a-credential');
    expect(requests.length, 1);
    expect(requests.single.url.path, '/api/offline-reconciliation/mobile-wins');
    final body = jsonDecode(requests.single.body) as Map;
    expect(body['baseline_snapshot'], wire['snapshot']);
    expect(
        body['baseline_fingerprint'], wire['authority']['state_fingerprint']);
    expect(utf8.encode(jsonEncode(body['operations'])),
        utf8.encode(jsonEncode(operations)));
    expect(body['reconciliation_id'], 'synthetic-p0-existing-mw');
    // No AppState finalization, acknowledgment or large-restore API is invoked.
    client.close();
  });

  test(
      'existing MW preflight still rejects invalid authoritative B before HTTP',
      () async {
    var requests = 0;
    final snapshot = jsonDecode(jsonEncode(evidence['wire']['snapshot']))
        as Map<String, dynamic>;
    (snapshot['data']['app_settings'] as List)
            .singleWhere((r) => r['key'] == 'cash_flow_balance')['value'] =
        '\ufeff1000';
    final client = MockClient((_) async {
      requests++;
      return http.Response('{}', 200);
    });
    final api =
        MoneyNoteApiClient(client: client, baseUrl: 'https://p0.synthetic');
    await expectLater(
        api.reconcileOfflineMobileWins(
            reconciliationId: 'synthetic-p0-invalid-b',
            baselineFingerprint: evidence['wire']['authority']
                ['state_fingerprint'],
            baselineSnapshot: snapshot,
            operations: [],
            mobileArtifactSha256: 'a' * 64,
            expectedServerFingerprint: 'b' * 64,
            confirmServerChanged: false,
            password: 'synthetic-not-a-credential'),
        throwsA(isA<MoneyNoteApiException>()
            .having((e) => e.code, 'code', 'invalid_money_input')));
    expect(requests, 0);
    client.close();
  });

  test(
      'API write preflight is not broadened by nested read-compatible settings',
      () async {
    var requests = 0;
    final client = MockClient((_) async {
      requests++;
      return http.Response('{}', 200);
    });
    final api =
        MoneyNoteApiClient(client: client, baseUrl: 'https://p0.synthetic');
    await expectLater(
        api.reconcileOfflineMobileWins(
          reconciliationId: 'synthetic-p0-input-preflight',
          baselineFingerprint: baselineFixture().serverStateFingerprint!,
          baselineSnapshot: baselineFixture().authoritativeSnapshot!,
          operations: [
            {
              'payload': {
                'settings': {'cash_flow_balance': '\u001c1000\u001f'}
              }
            }
          ],
          mobileArtifactSha256: 'a' * 64,
          expectedServerFingerprint: 'b' * 64,
          confirmServerChanged: false,
          password: 'synthetic-not-a-credential',
        ),
        throwsA(isA<MoneyNoteApiException>()
            .having((e) => e.code, 'code', 'invalid_money_input')));
    expect(requests, 0);
    client.close();
  });
}
