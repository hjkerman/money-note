@Timeout(Duration(minutes: 3))
library;

import 'dart:async';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/offline_mode_fixtures.dart';
import 'support/segmented_e2_fixture.dart';

class _SessionApi extends MoneyNoteApiClient {
  _SessionApi(BackendBridge bridge)
      : super(client: bridge, baseUrl: syntheticOrigin);
  @override
  Future<void> health({Duration timeout = const Duration(seconds: 15)}) async {}
  @override
  Future<AuthUser> login(String username, String password) async =>
      baselineFixture().user;
  @override
  Future<void> logout() => saveSession(null);
  @override
  Future<CashFlow> createCashFlow(
          {required String occurredOn,
          required String title,
          required int amount,
          required bool isPrimaryIncome}) async =>
      CashFlow(
          id: 777,
          occurredOn: occurredOn,
          title: title,
          amountValue: amount,
          sortOrder: 0,
          isPrimaryIncome: isPrimaryIncome);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late Directory root;
  late _SessionApi api;
  late AppState state;
  SegmentedClientStore? store;
  late OfflineStore legacy;
  var disposed = false;
  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    disposed = false;
    root = Directory.systemTemp.createTempSync('money-note-e3-authority-');
    bridge = await BackendBridge.start();
    api = _SessionApi(bridge);
    await api.saveSession(bridge.token);
    legacy = OfflineStore(directoryProvider: () async => root);
    state = AppState(api, offlineStore: legacy)..user = baselineFixture().user;
  });
  tearDown(() async {
    if (!disposed) state.dispose();
    store?.close();
    store = null;
    await bridge.dispose();
    root.deleteSync(recursive: true);
  });
  SegmentedClientStore open({StoreFault? fault}) => store =
      SegmentedClientStore.open(root, GenerationFixture(bridge.fixture).cache,
          publication: true, fault: fault);
  void persisted(int sequence) {
    final db = sqlite3.open(store!.path);
    expect(db.select('SELECT sequence FROM accepted').single['sequence'],
        sequence);
    expect(db.select('PRAGMA foreign_key_check'), isEmpty);
    db.close();
  }

  test(
      'actual D3a/D3b acquisition and AppState-owned publication; no legacy/UI install',
      () async {
    await legacy.replaceBaseline(baselineFixture());
    await legacy.beginOnlineWrite(
        1); // E3 must not acknowledge even this pending input.
    final journal = File('${root.path}/offline-mode/journal.ndjson')
      ..writeAsStringSync('synthetic frozen journal bytes\n');
    final files = Directory('${root.path}/offline-mode')
        .listSync()
        .whereType<File>()
        .toList();
    final before = {for (final f in files) f.path: f.readAsBytesSync()};
    final summary = baselineFixture().summary;
    state.summary = summary;
    final db = open();
    final result = await state.publishSegmentedForIsolatedUse(db);
    expect(result.sequence, 1);
    expect(result.target.syncRoot,
        GenerationFixture(bridge.fixture).target.syncRoot);
    persisted(1);
    expect(identical(state.summary, summary), isTrue);
    expect(state.isOnline, isTrue);
    expect(journal.existsSync(), isTrue);
    for (final f in files) {
      expect(f.readAsBytesSync(), before[f.path]);
    }
    expect((await legacy.loadPendingOnlineWrite(1)), isNotNull);
    expect(state.lastSuccessfulSyncAt, isNull);
    expect(bridge.objectRequests, greaterThan(0));
  });

  for (final change in [
    'user',
    'mode',
    'credential',
    'logout',
    'disposed',
    'cancelled'
  ]) {
    test('final pre-COMMIT $change change rejects and releases prepared pins',
        () async {
      var once = false;
      Future<void>? changed;
      final cancellation = SyncCancellation();
      final db = open(fault: (point) {
        if (point != 'before_publication_commit' || once) return;
        once = true;
        switch (change) {
          case 'user':
            state.user = null;
          case 'mode':
            state.connectivityMode = ConnectivityMode.offline;
          case 'credential':
            changed = api.saveSession('synthetic-replacement');
          case 'logout':
            changed = state.logout();
          case 'disposed':
            state.dispose();
            disposed = true;
          case 'cancelled':
            cancellation.cancel();
        }
      });
      await expectLater(
          state.publishSegmentedForIsolatedUse(db, cancellation: cancellation),
          throwsA(
              anyOf(isA<MoneyNoteApiException>(), isA<SegmentedException>())));
      await changed;
      persisted(0);
      final direct = sqlite3.open(db.path);
      expect(direct.select('SELECT * FROM generations'), isEmpty);
      expect(direct.select('SELECT * FROM generation_objects'), isEmpty);
      direct.close();
    });
  }
  for (final change in [
    'logout',
    'same-user-login',
    'newer-legacy-refresh',
    'mutation',
    'offline-transition'
  ]) {
    test('$change after acquisition invalidates ORIGINAL coordinator ticket',
        () async {
      final reached = Completer<void>(), resume = Completer<void>();
      if (change == 'offline-transition') {
        await legacy.replaceBaseline(baselineFixture());
      }
      var paused = false;
      bridge.before = (path) async {
        if (!paused &&
            path.contains('/observations/') &&
            !path.endsWith('/objects')) {
          paused = true;
          reached.complete();
          await resume.future;
        }
      };
      final db = open(), pending = state.publishSegmentedForIsolatedUse(db);
      final rejected = expectLater(
          pending,
          throwsA(anyOf(
              isA<MoneyNoteApiException>(),
              isA<AcquisitionFailure>().having((e) => e.code, 'code',
                  anyOf('AUTH_REQUIRED', 'AUTHENTICATION_CHANGED')))));
      await reached.future;
      switch (change) {
        case 'logout':
          await state.logout();
        case 'same-user-login':
          await state.login('synthetic', 'synthetic');
        case 'newer-legacy-refresh':
          try {
            await state.refresh();
          } on MoneyNoteApiException {/* synthetic ASGI has no legacy route */}
        case 'mutation':
          await state.createCashFlow(
              occurredOn: '2026-09-17',
              title: '합성 race',
              amount: 1,
              isIncome: false,
              isPrimaryIncome: false);
          expect(await legacy.loadPendingOnlineWrite(1), isNotNull);
        case 'offline-transition':
          expect(await state.enterOfflineMode(), isTrue);
      }
      resume.complete();
      await rejected;
      persisted(0);
    });
  }
  test(
      'new segmented request invalidates older ticket even when acquisition is busy',
      () async {
    final reached = Completer<void>(), resume = Completer<void>();
    var paused = false;
    bridge.before = (path) async {
      if (!paused && path.endsWith('/observations')) {
        paused = true;
        reached.complete();
        await resume.future;
      }
    };
    final db = open(), first = state.publishSegmentedForIsolatedUse(db);
    final rejected = expectLater(first, throwsA(isA<MoneyNoteApiException>()));
    await reached.future;
    await expectLater(
        state.publishSegmentedForIsolatedUse(db),
        throwsA(isA<AcquisitionFailure>()
            .having((e) => e.code, 'code', 'ACQUISITION_BUSY')));
    resume.complete();
    await rejected;
    persisted(0);
  });
  test('post-COMMIT authority loss is reported as committed, never rollback',
      () async {
    final db = open(fault: (point) {
      if (point == 'after_publication_commit') state.user = null;
    });
    await expectLater(
        state.publishSegmentedForIsolatedUse(db),
        throwsA(isA<PublicationCommittedException>()
            .having((e) => e.cause, 'cause', isA<MoneyNoteApiException>())));
    persisted(1);
    final direct = sqlite3.open(db.path);
    final pointer = direct.select('SELECT * FROM accepted').single;
    expect(
        direct.select('SELECT * FROM generation_roots WHERE generation_id=?',
            [pointer['current_id']]),
        hasLength(4));
    final retained = direct.select('''WITH RECURSIVE closure(hash) AS (
      SELECT hash FROM generation_roots WHERE generation_id=?
      UNION SELECT e.child FROM edges e JOIN closure c ON e.parent=c.hash)
      SELECT hash FROM closure''', [pointer['current_id']]);
    expect(retained.map((r) => r['hash']).toSet(),
        GenerationFixture(bridge.fixture).objects.keys.toSet());
    direct.close();
    expect(state.lastSuccessfulSyncAt, isNull);
    expect(state.summary, isNull);
  });
  test('default AppState construction never opens segmented storage or fetches',
      () {
    expect(Directory('${root.path}/segmented-store-v1').existsSync(), isFalse);
    expect(bridge.objectRequests, 0);
    expect(bridge.manifestRequests, 0);
  });
  test('ordinary ONLINE only: no finalizing bypass API', () async {
    state.connectivityMode = ConnectivityMode.reconciliationFinalizing;
    await expectLater(state.publishSegmentedForIsolatedUse(open()),
        throwsA(isA<SegmentedException>()));
    persisted(0);
    expect(bridge.manifestRequests, 0);
  });
  for (final mismatch in ['principal', 'origin']) {
    test('$mismatch mismatch rejected before acquisition', () async {
      final target = GenerationFixture(bridge.fixture).target.toJson()
        ..remove('sync_root');
      if (mismatch == 'principal') target['principal_id'] = 2;
      target['sync_root'] = objectHash('view', encodeC1(target));
      final cache = CacheNamespace.forTarget(
          mismatch == 'origin' ? 'https://another.synthetic' : syntheticOrigin,
          SyncTarget.parse(target));
      store = SegmentedClientStore.open(root, cache, publication: true);
      await expectLater(state.publishSegmentedForIsolatedUse(store!),
          throwsA(isA<SegmentedException>()));
      expect(bridge.manifestRequests, 0);
      persisted(0);
    });
  }
  test('E1 default schema cannot silently become publisher profile', () async {
    store = SegmentedClientStore.open(
        root, GenerationFixture(bridge.fixture).cache);
    await expectLater(state.publishSegmentedForIsolatedUse(store!),
        throwsA(isA<SegmentedException>()));
    final direct = sqlite3.open(store!.path);
    expect(direct.select('PRAGMA user_version').single.values.first, 1);
    expect(
        direct.select("SELECT name FROM sqlite_master WHERE name='accepted'"),
        isEmpty);
    direct.close();
    expect(bridge.manifestRequests, 0);
  });
}
