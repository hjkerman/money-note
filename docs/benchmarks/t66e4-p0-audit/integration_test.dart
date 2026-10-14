@Timeout(Duration(minutes: 3))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/offline/online_write_state.dart';

import '../../../mobile/test/support/offline_mode_fixtures.dart';

const special = '\u001c+0001000.00\u001f';
const keys = [
  'scheduled_income',
  'cash_flow_balance',
  'card_limit',
  'base_next_month_liquidity',
  'liquidity_status',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final repository = Directory.current.parent.path;
  late Map<String, dynamic> evidence;
  late Directory root;
  late OfflineStore store;
  late OfflineBaseline baseline;
  late File journal, pending;
  late PendingOnlineWrite marker;
  final results = <Map<String, dynamic>>[];
  Map<String, dynamic> baselineWire() {
    final wire = evidence['wire'] as Map<String, dynamic>;
    return {
      ...wire['state'] as Map<String, dynamic>,
      'schema_version': 4,
      'synced_at': wire['snapshot']['exported_at'],
      'user': baselineFixture().toJson()['user'],
      'authoritative_snapshot': wire['snapshot'],
      'server_state_fingerprint': wire['authority']['state_fingerprint'],
      'resolved_reconciliation_id': null,
      'discount_policy_defaults': wire['authority']['discount_policy_defaults'],
    };
  }

  List<OfflineJournalOperation> seeded() => [
    for (final (index, value) in [
      ' \t+0001000.00\n',
      '\ufeff-0000.0\ufeff',
      '-0007.000',
    ].indexed)
      OfflineJournalOperation(
        operationId: 'independent-fixed-$index',
        type: OfflineOperationType.createCashFlow,
        payload: {
          'amount_value': value,
          'occurred_on': '2026-10-14',
          'title': '한글 e\u0301 😀',
        },
        createdAt: DateTime.utc(2026, 10, 14),
        sequence: index + 1,
      ),
  ];
  setUpAll(() async {
    final run = await Process.run('$repository/.venv/bin/python', [
      '$repository/docs/benchmarks/t66e4-contract/probe.py',
    ]);
    expect(run.exitCode, 0, reason: run.stderr as String);
    evidence = jsonDecode(run.stdout as String) as Map<String, dynamic>;
  });
  setUp(() async {
    root = Directory.systemTemp.createTempSync('mn-e4-p0-independent-');
    File('${root.path}/audit-owned').writeAsStringSync('E4-P0 SYNTHETIC AUDIT');
    store = OfflineStore(
      directoryProvider: () async => root,
      clock: () => DateTime.utc(2026, 10, 14),
    );
    baseline = OfflineBaseline.fromJson(baselineWire());
    await store.replaceBaseline(baseline);
    journal = File('${root.path}/offline-mode/journal.ndjson');
    journal.writeAsStringSync(
      '${seeded().map((o) => jsonEncode(o.toJson()).replaceAll('\":', '\": ')).join('\n')}\n',
      flush: true,
    );
    marker = await store.beginOnlineWrite(
      1,
      retryIdentity: 'synthetic-fixed-retry',
    );
    pending = File('${root.path}/offline-mode/online-write-1.json');
  });
  tearDown(() => root.deleteSync(recursive: true));
  tearDownAll(() {
    final output = Platform.environment['E4_P0_INTEGRATION_OUTPUT'];
    if (output != null) File(output).writeAsStringSync(jsonEncode(results));
  });

  test('original backend/E1-compatible representation is accepted only at authoritative legacy boundary', () {
    final vector = (evidence['vectors'] as List).singleWhere(
      (v) => v['value'] == special,
    ) as Map;
    expect(vector['segmented'], true);
    expect(vector['legacy_server'], true);
    final wire = evidence['wire'] as Map<String, dynamic>;
    final before = jsonEncode(wire);
    final bundle = AuthoritativeBundle.decode(utf8.encode(before))
        .toCoherentBundle(baseline.user);
    expect(bundle.candidate.settings.values['cash_flow_balance'], special);
    expect(baseline.settings.values['cash_flow_balance'], special);
    expect(() => exactMoney(special), throwsFormatException);
    expect(jsonEncode(wire), before);
    expect(
      baseline.serverStateFingerprint,
      isNot(evidence['fixture']['manifest']['target']['sync_root']),
    );
  });

  test('fresh Python process reads durable raw bytes and independently recomputes v7 fingerprint and v4 lineage', () async {
    final run = await Process.run('$repository/.venv/bin/python', [
      '$repository/docs/benchmarks/t66e4-p0-audit/inspect_state.py',
      root.path,
    ]);
    expect(run.exitCode, 0, reason: run.stderr as String);
    final observed = jsonDecode(run.stdout as String) as Map<String, dynamic>;
    expect(observed['fingerprint'], baseline.serverStateFingerprint);
    expect(observed['lineage'], store.recoveryLineageFingerprint(baseline));
    expect(observed['normalization_changes_fingerprint'], true);
    expect(observed['original_codepoints'], special.runes.toList());
    final reopened = OfflineStore(directoryProvider: () async => root);
    expect((await reopened.loadBaseline())!.toJson(), baseline.toJson());
    results.add({'case': 'fresh-persisted', 'result': 'PASS', ...observed});
  });

  test('failed baseline authority publication preserves existing B, J and pending bytes', () async {
    final b = File('${root.path}/offline-mode/baseline.json'),
        beforeB = b.readAsBytesSync();
    final beforeJ = journal.readAsBytesSync(),
        beforeP = pending.readAsBytesSync();
    await expectLater(
      store.replaceBaseline(
        baselineFixture(),
        beforePublish: () => throw StateError('synthetic guard'),
      ),
      throwsStateError,
    );
    expect(b.readAsBytesSync(), beforeB);
    expect(journal.readAsBytesSync(), beforeJ);
    expect(pending.readAsBytesSync(), beforeP);
    expect(
      root
          .listSync(recursive: true)
          .whereType<File>()
          .where((f) => f.path.endsWith('.tmp')),
      isEmpty,
    );
  });

  test('existing formatted journal bytes survive reopen and replay without input normalization', () async {
    final before = journal.readAsBytesSync(),
        beforeP = pending.readAsBytesSync();
    final loaded = await OfflineStore(directoryProvider: () async => root)
        .loadJournal();
    expect(
      loaded.map((o) => o.toJson()).toList(),
      seeded().map((o) => o.toJson()).toList(),
    );
    final requests = <http.Request>[];
    final client = MockClient((request) async {
      requests.add(request);
      return http.Response('{}', 200);
    });
    final api = MoneyNoteApiClient(
      client: client,
      baseUrl: 'https://independent-p0.synthetic',
    );
    await api.reconcileOfflineMobileWins(
      reconciliationId: 'synthetic-fixed',
      baselineFingerprint: baseline.serverStateFingerprint!,
      baselineSnapshot: baseline.authoritativeSnapshot!,
      operations: loaded.map((o) => o.toJson()).toList(),
      mobileArtifactSha256: 'a' * 64,
      expectedServerFingerprint: 'b' * 64,
      confirmServerChanged: false,
      password: 'synthetic-only',
    );
    final body = jsonDecode(requests.single.body) as Map;
    expect(body['operations'], seeded().map((o) => o.toJson()).toList());
    expect(body['baseline_snapshot'], baseline.authoritativeSnapshot);
    expect(journal.readAsBytesSync(), before);
    expect(pending.readAsBytesSync(), beforeP);
    client.close();
  });

  test('old accepted BOM/leading-zero input appends exact raw value and retains previous journal prefix', () async {
    final before = journal.readAsBytesSync(),
        beforeP = pending.readAsBytesSync();
    const value = '\ufeff+00009.000\ufeff';
    expect(exactMoney(value), 9);
    final operation = await store.appendOperation(
      type: OfflineOperationType.createCashFlow,
      payload: {
        'amount_value': value,
        'occurred_on': '2026-10-14',
        'title': '독립 입력',
      },
      baseline: baseline,
    );
    expect(operation.sequence, 4);
    expect(operation.payload['amount_value'], value);
    expect(journal.readAsBytesSync().take(before.length).toList(), before);
    final rows = await OfflineStore(directoryProvider: () async => root)
        .loadJournal();
    expect(
      rows.map((o) => o.operationId).take(3).toList(),
      seeded().map((o) => o.operationId).toList(),
    );
    expect(rows.last.payload['amount_value'], value);
    expect(pending.readAsBytesSync(), beforeP);
  });

  test(
    'pending acknowledgment still requires original token and never rewrites J',
    () async {
      final beforeP = pending.readAsBytesSync(),
          beforeJ = journal.readAsBytesSync();
      await expectLater(
        store.completeOnlineWrite(
          const PendingOnlineWrite(
            1,
            'wrong-token',
            OnlineWriteStatus.outcomeUnknown,
          ),
        ),
        throwsA(isA<OfflinePersistenceException>()),
      );
      expect(pending.readAsBytesSync(), beforeP);
      expect(journal.readAsBytesSync(), beforeJ);
      await store.savePendingOnlineWrite(marker.committed());
      final reloaded = (await OfflineStore(directoryProvider: () async => root)
          .loadPendingOnlineWrite(1))!;
      expect(reloaded.token, marker.token);
      expect(reloaded.retryIdentity, marker.retryIdentity);
      await store.completeOnlineWrite(reloaded);
      expect(pending.existsSync(), false);
      expect(journal.readAsBytesSync(), beforeJ);
    },
  );

  test('recovery artifact permits compatible B and original J but never permits nested compatible J input', () async {
    const metadata = OfflineWorkspaceMetadata(
      mode: ConnectivityMode.reconciliationRequired,
      reconciliationId: 'synthetic-fixed',
      reconciliationChoice: ReconciliationChoice.applyToServer,
      phase: ReconciliationPhase.preparing,
    );
    final beforeJ = journal.readAsBytesSync(),
        beforeP = pending.readAsBytesSync();
    final artifact = await store.createMobileRecoveryArtifact(
      baseline: baseline,
      operations: seeded(),
      metadata: metadata,
    );
    expect(
      await store.verifyMobileRecoveryArtifact(
        artifact.filename,
        expectedBaseline: baseline,
        expectedOperations: seeded(),
      ),
      artifact.sha256,
    );
    final bad = OfflineJournalOperation(
      operationId: 'invalid-nested',
      type: OfflineOperationType.createCashFlow,
      payload: {
        'wrapper': [
          {
            'app_settings': [
              {'key': 'cash_flow_balance', 'value': special},
            ],
          },
        ],
      },
      createdAt: DateTime.utc(2026, 10, 14),
      sequence: 4,
    );
    await expectLater(
      store.createMobileRecoveryArtifact(
        baseline: baseline,
        operations: [bad],
        metadata: metadata,
      ),
      throwsFormatException,
    );
    expect((await store.listMobileRecoveryArtifacts()).length, 1);
    expect(journal.readAsBytesSync(), beforeJ);
    expect(pending.readAsBytesSync(), beforeP);
  });

  test(
    'MW B compatibility cannot relax nested J request admission or issue HTTP',
    () async {
      var requests = 0;
      final client = MockClient((_) async {
        requests++;
        return http.Response('{}', 200);
      });
      final api = MoneyNoteApiClient(
        client: client,
        baseUrl: 'https://independent-p0.synthetic',
      );
      await expectLater(
        api.reconcileOfflineMobileWins(
          reconciliationId: 'synthetic-invalid-j',
          baselineFingerprint: baseline.serverStateFingerprint!,
          baselineSnapshot: baseline.authoritativeSnapshot!,
          operations: [
            {
              'payload': {
                'wrapper': [
                  {
                    'app_settings': [
                      {'key': 'card_limit', 'value': special},
                    ],
                  },
                ],
              },
            },
          ],
          mobileArtifactSha256: 'a' * 64,
          expectedServerFingerprint: 'b' * 64,
          confirmServerChanged: false,
          password: 'synthetic-only',
        ),
        throwsA(
          isA<MoneyNoteApiException>().having(
            (e) => e.code,
            'code',
            'invalid_money_input',
          ),
        ),
      );
      expect(requests, 0);
      client.close();
    },
  );

  for (final key in keys) {
    for (final shape in ['settings', 'app_settings']) {
      test(
        'actual append rejects read-compatible nested $shape/$key and preserves bytes',
        () async {
          final beforeJ = journal.readAsBytesSync(),
              beforeP = pending.readAsBytesSync();
          final payload = {
            'wrapper': [
              shape == 'settings'
                  ? {
                      'settings': {key: special},
                    }
                  : {
                      'app_settings': [
                        {'key': key, 'value': special},
                      ],
                    },
            ],
          };
          await expectLater(
            store.appendOperation(
              type: OfflineOperationType.createCashFlow,
              payload: payload,
              baseline: baseline,
            ),
            throwsFormatException,
          );
          expect(journal.readAsBytesSync(), beforeJ);
          expect(pending.readAsBytesSync(), beforeP);
          expect((await store.loadJournal()).length, 3);
        },
      );
    }
  }
}
