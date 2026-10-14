// 독립 authority race: 계측 source copy를 사용하지 않는 실제 AppState 경로다.
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

class Adapter extends http.BaseClient {
  Adapter(this.transport);
  final FixtureTransport transport;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final raw = await request.finalize().toBytes();
    if (!request.url.path.startsWith('/api/sync/v1/'))
      return http.StreamedResponse(Stream.value(utf8.encode('{}')), 404);
    final reply = await transport.exchange(
      request.method,
      request.url.path,
      raw.isEmpty ? null : Uint8List.fromList(raw),
      SyncCancellation(),
      8 * 1048576,
    );
    return http.StreamedResponse(
      Stream.value(reply.bytes),
      reply.status,
      contentLength: reply.bytes.length,
    );
  }
}

class Api extends MoneyNoteApiClient {
  Api(Adapter adapter) : super(client: adapter, baseUrl: syntheticOrigin);
  void Function()? credentialRead;
  @override
  T withIsolatedTransport<T>(
    T Function(http.Client, String, String? Function()) create,
  ) => super.withIsolatedTransport(
    (client, origin, get) => create(client, origin, () {
      credentialRead?.call();
      return get();
    }),
  );
  @override
  Future<void> health({Duration timeout = const Duration(seconds: 15)}) async {}
  @override
  Future<AuthUser> me() async => baselineFixture().user;
  @override
  Future<AuthUser> login(String username, String password) async =>
      baselineFixture().user;
  @override
  Future<void> logout() => saveSession(null);
  @override
  Future<CashFlow> createCashFlow({
    required String occurredOn,
    required String title,
    required int amount,
    required bool isPrimaryIncome,
  }) async => CashFlow(
    id: 909,
    occurredOn: occurredOn,
    title: title,
    amountValue: amount,
    sortOrder: 0,
    isPrimaryIncome: isPrimaryIncome,
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final directory = Platform.environment['E3_AUTH_CORPUS']!;
  final first = GenerationFixture(
    jsonDecode(File('$directory/4-0.json').readAsStringSync())
        as Map<String, dynamic>,
  );
  final second = GenerationFixture(
    jsonDecode(File('$directory/4-1.json').readAsStringSync())
        as Map<String, dynamic>,
  );
  late Directory root;
  late Api api;
  late AppState app;
  late FixtureTransport transport;
  late SegmentedClientStore store;
  late OfflineStore legacy;
  void Function(String)? inject;
  Map<String, List<int>> legacyBytes() => {
    for (final file in Directory(
      '${root.path}/offline-mode',
    ).listSync(recursive: true).whereType<File>())
      file.path: file.readAsBytesSync(),
  };
  Map<String, Object?> inspect() {
    final db = sqlite3.open(store.path);
    try {
      final p = db.select('SELECT * FROM accepted').single;
      final receipt =
          db.select('SELECT receipt FROM generations WHERE id=?', [
                p['current_id'],
              ]).single['receipt']
              as List<int>;
      final value = jsonDecode(utf8.decode(receipt)) as Map;
      expect(db.select('PRAGMA foreign_key_check'), isEmpty);
      return {
        'sequence': p['sequence'],
        'id': p['current_id'],
        'previous': p['previous_id'],
        'target': value['target']['sync_root'],
      };
    } finally {
      db.close();
    }
  }

  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    inject = null;
    root = Directory.systemTemp.createTempSync('e3-independent-authority-');
    transport = FixtureTransport(first);
    api = Api(Adapter(transport));
    await api.saveSession('independent-test-token');
    legacy = OfflineStore(directoryProvider: () async => root);
    await legacy.replaceBaseline(baselineFixture());
    app = AppState(api, offlineStore: legacy)..user = baselineFixture().user;
    store = SegmentedClientStore.open(
      root,
      first.cache,
      publication: true,
      fault: (point) => inject?.call(point),
    );
    await app.publishSegmentedForIsolatedUse(store);
    transport.fixture = second;
  });
  tearDown(() {
    app.dispose();
    store.close();
    root.deleteSync(recursive: true);
  });

  for (final scenario in [
    'different-user',
    'logout',
    'credential-gap',
    'offline',
    'finalizing',
    'blocked',
    'cancel',
    'reentrant-credential',
  ]) {
    test('accepted G1 survives final authority race: $scenario', () async {
      final before = inspect(),
          files = legacyBytes(),
          cancel = SyncCancellation();
      Future<void>? changed;
      var reachedFinalHook = false;
      inject = (point) {
        if (point != 'before_publication_commit') return;
        reachedFinalHook = true;
        switch (scenario) {
          case 'different-user':
            app.user = AuthUser(
              id: 2,
              username: 'synthetic-other',
              displayName: '합성 다른 사용자',
              sharePinNeedsChange: false,
            );
          case 'logout':
            changed = app.logout();
          case 'credential-gap':
            changed = api.saveSession(
              'independent-replacement-before-generation',
            );
          case 'offline':
            app.connectivityMode = ConnectivityMode.offline;
          case 'finalizing':
            app.connectivityMode = ConnectivityMode.reconciliationFinalizing;
          case 'blocked':
            app.connectivityMode = ConnectivityMode.persistenceRecoveryBlocked;
          case 'cancel':
            cancel.cancel();
          case 'reentrant-credential':
            api.credentialRead = () {
              app.user = null;
            };
        }
      };
      await expectLater(
        app.publishSegmentedForIsolatedUse(store, cancellation: cancel),
        throwsA(isA<Object>()),
      );
      await changed;
      expect(reachedFinalHook, isTrue);
      expect(inspect(), before);
      expect(legacyBytes(), files);
      expect(app.summary, isNull);
      expect(app.lastSuccessfulSyncAt, isNull);
    });
  }
  for (final scenario in [
    'same-user-login',
    'mutation',
    'newer-legacy',
    'newer-segmented',
    'logout',
  ]) {
    test(
      'accepted G1 survives acquisition authority race: $scenario',
      () async {
        final reached = Completer<void>(), resume = Completer<void>();
        var held = false;
        transport.before = (method, path, body) async {
          if (method == 'DELETE' && !held) {
            held = true;
            reached.complete();
            await resume.future;
          }
          return null;
        };
        final before = inspect(),
            pending = app.publishSegmentedForIsolatedUse(store);
        Object? failure;
        final observed = pending.then<void>(
          (_) => fail('stale candidate committed'),
          onError: (Object e) {
            failure = e;
          },
        );
        await reached.future;
        switch (scenario) {
          case 'same-user-login':
            await app.login('synthetic', 'synthetic');
          case 'logout':
            await app.logout();
          case 'mutation':
            await app.createCashFlow(
              occurredOn: '2026-09-17',
              title: '독립 합성 mutation',
              amount: 1,
              isIncome: false,
              isPrimaryIncome: false,
            );
          case 'newer-legacy':
            try {
              await app.refresh();
            } on Object {
              /* legacy route가 없는 시험 transport다. */
            }
          case 'newer-segmented':
            await expectLater(
              app.publishSegmentedForIsolatedUse(store),
              throwsA(isA<Object>()),
            );
        }
        final files = legacyBytes();
        resume.complete();
        await observed;
        expect(failure, isNotNull);
        expect(inspect(), before);
        expect(legacyBytes(), files);
      },
    );
  }
  test('successful G1 to G2 publishes only internal state and preserves frozen files', () async {
    final files = legacyBytes();
    final result = await app.publishSegmentedForIsolatedUse(store);
    expect(result.sequence, 2);
    expect(inspect()['target'], second.target.syncRoot);
    expect(legacyBytes(), files);
    expect(app.summary, isNull);
    expect(app.lastSuccessfulSyncAt, isNull);
  });
  test('queued microtask is after synchronous publication COMMIT', () async {
    var scheduled = false;
    inject = (point) {
      if (point == 'before_publication_commit' && !scheduled) {
        scheduled = true;
        scheduleMicrotask(() => app.user = null);
      }
    };
    await expectLater(
      app.publishSegmentedForIsolatedUse(store),
      throwsA(isA<PublicationCommittedException>()),
    );
    expect(inspect()['sequence'], 2);
    expect(inspect()['target'], second.target.syncRoot);
    expect(app.summary, isNull);
  });
}
