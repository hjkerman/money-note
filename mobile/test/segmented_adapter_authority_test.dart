@Timeout(Duration(minutes: 5))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/offline_mode_fixtures.dart';
import 'support/segmented_e2_fixture.dart';

class _OfflineBarrier extends OfflineStore {
  _OfflineBarrier(Directory root) : super(directoryProvider: () async => root);
  Completer<void>? entered, release;
  void pause() {
    entered = Completer<void>();
    release = Completer<void>();
  }

  @override
  Future<OfflineWorkspaceMetadata> loadMetadata() async {
    if (entered != null && !entered!.isCompleted) entered!.complete();
    await release?.future;
    return super.loadMetadata();
  }
}

class _Api extends MoneyNoteApiClient {
  _Api(this.wire, http.Client client)
      : super(client: client, baseUrl: syntheticOrigin);
  final Map<String, dynamic> wire;
  @override
  Future<void> logout() => saveSession(null);
  @override
  Future<AuthUser> login(String username, String password) async => AuthUser(
      id: 1,
      username: 'synthetic',
      displayName: '합성',
      sharePinNeedsChange: false,
      sessionToken: 'synthetic-new-session');
  @override
  Future<Uint8List> authoritativeStateBytes() async =>
      Uint8List.fromList(utf8.encode(jsonEncode(wire)));
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Map<String, dynamic> oracle;
  late GenerationFixture fixture;
  late Directory root;
  late SegmentedClientStore store;
  late _OfflineBarrier offline;
  late _Api api;
  late AppState state;
  late http.Client client;
  var requests = 0;
  setUpAll(() async {
    final repo = Directory.current.parent.path;
    final run = await Process.run('$repo/.venv/bin/python',
        ['$repo/mobile/test/support/e4_backend_oracle.py']);
    expect(run.exitCode, 0, reason: run.stderr as String);
    oracle = jsonDecode(run.stdout as String) as Map<String, dynamic>;
    fixture = GenerationFixture(oracle['fixture']);
  });
  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    root = Directory.systemTemp.createTempSync('mn-e4-authority-');
    store = SegmentedClientStore.open(root, fixture.cache, publication: true);
    final base = await store.recoverAcceptedGeneration();
    final acquired =
        await IncrementalFetcher(store, FixtureTransport(fixture)).acquire();
    final version = store.publicationDataVersion;
    final proof = await store.verifyPublicationCandidate(
        acquired.manifest, base,
        verifiedDataVersion: version);
    final prepared = store.prepareGeneration(
        syncUuid(), acquired.stagingId, proof, base,
        verifiedDataVersion: version);
    store.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
    offline = _OfflineBarrier(root);
    requests = 0;
    client = MockClient((_) async {
      requests++;
      return http.Response('{}', 200);
    });
    api = _Api(oracle['wire'], client);
    await api.saveSession('synthetic-original-session');
    state = AppState(api, offlineStore: offline)..user = baselineFixture().user;
  });
  tearDown(() {
    state.dispose();
    store.close();
    client.close();
    root.deleteSync(recursive: true);
  });
  void persisted() {
    final direct = sqlite3.open(store.path);
    expect(
        direct.select('SELECT sequence FROM accepted').single['sequence'], 1);
    expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
    direct.close();
  }

  Future<void> pausedRace(Future<void> Function() change) async {
    final marker = await offline.beginOnlineWrite(1);
    final file = File('${root.path}/offline-mode/online-write-1.json');
    final before = file.readAsBytesSync();
    offline.pause();
    final result =
        state.readSegmentedForIsolatedUse(store, includePending: true);
    await offline.entered!.future;
    await change();
    offline.release!.complete();
    await expectLater(result, throwsA(isA<Exception>()));
    expect(file.readAsBytesSync(), before);
    expect((await offline.loadPendingOnlineWrite(1))!.token, marker.token);
    persisted();
  }

  test(
      'isolated AppState read uses existing authority, no HTTP/UI/B/J installation',
      () async {
    final original = baselineFixture().summary;
    state.summary = original;
    var notifications = 0;
    state.addListener(() => notifications++);
    final read = await state.readSegmentedForIsolatedUse(store);
    expect(read.segmented.target.syncRoot, fixture.target.syncRoot);
    expect(identical(state.summary, original), true);
    expect(state.isOnline, true);
    expect(requests, 0);
    expect(notifications, 0);
    expect(Directory('${root.path}/offline-mode').existsSync(), false);
    persisted();
  });
  test(
      'explicit full legacy read still does not install baseline or change mode',
      () async {
    final read =
        await state.readSegmentedForIsolatedUse(store, materializeLegacy: true);
    expect(read.legacy!.envelope.snapshot, oracle['expected_snapshot']);
    expect(read.legacy!.envelope.fingerprint, oracle['expected_fingerprint']);
    expect(await offline.loadBaseline(), null);
    expect(state.summary, null);
    expect(state.isOnline, true);
    expect(requests, 0);
  });
  for (final committed in [false, true]) {
    test(
        'pending marker committed=$committed remains separate, never GET acknowledgment',
        () async {
      final marker = await offline.beginOnlineWrite(1);
      if (committed) {
        await offline.savePendingOnlineWrite(marker.committed());
      }
      final file = File('${root.path}/offline-mode/online-write-1.json');
      final before = file.readAsBytesSync();
      final read =
          await state.readSegmentedForIsolatedUse(store, includePending: true);
      expect(read.pendingOnlineWrite!.status,
          (await offline.loadPendingOnlineWrite(1))!.status);
      expect(file.readAsBytesSync(), before);
      expect(state.lastSubmitServerCommitted, false);
      persisted();
    });
  }
  test('logout while pending-aware read prevents stale return', () async {
    await pausedRace(() => state.logout());
  });
  test('same-user reauthentication invalidates original coordinator ticket',
      () async {
    await pausedRace(
        () => state.login('synthetic', 'synthetic-not-a-real-password'));
  });
  test(
      'credential changes before AppState auth generation advances are rejected',
      () async {
    await pausedRace(() => api.saveSession('synthetic-other-session'));
  });
  test('newer legacy refresh invalidates original segmented read', () async {
    await pausedRace(() => state.refresh(notify: false));
  });
  test(
      'newer segmented read invalidates original request, not a recreated ticket',
      () async {
    await pausedRace(() async {
      await state.readSegmentedForIsolatedUse(store);
    });
  });
  test('mode transition while read waits is rejected', () async {
    await pausedRace(() async {
      state.connectivityMode = ConnectivityMode.offline;
    });
  });
  test('wrong selected user while read waits is rejected', () async {
    await pausedRace(() async {
      state.user = AuthUser(
          id: 2,
          username: 'other',
          displayName: '합성',
          sharePinNeedsChange: false);
    });
  });
  test('cancellation preserves accepted and pending state', () async {
    final cancel = SyncCancellation()..cancel();
    await expectLater(
        state.readSegmentedForIsolatedUse(store, cancellation: cancel),
        throwsA(isA<Exception>()));
    persisted();
  });
  test(
      'current OFFLINE pending view uses original frozen B, not accepted segmented G',
      () async {
    final b = baselineFixture();
    await offline.replaceBaseline(b);
    await offline.saveMetadata(OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint: offline.recoveryLineageFingerprint(b)));
    await offline.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: {
          'occurred_on': '2026-10-14',
          'title': '합성',
          'amount_value': 7,
          'is_primary_income': 0
        },
        baseline: b);
    state.connectivityMode = ConnectivityMode.offline;
    final folder = Directory('${root.path}/offline-mode');
    final before = {
      for (final f in folder.listSync().whereType<File>())
        f.path: f.readAsBytesSync()
    };
    final read =
        await state.readSegmentedForIsolatedUse(store, includePending: true);
    expect(read.pendingLegacy!.bundle.baseline.serverStateFingerprint,
        b.serverStateFingerprint);
    expect(read.pendingLegacy!.bundle.operations.single.sequence, 1);
    expect(
        read.pendingLegacy!.projection!.cashFlows.last.isOfflinePending, true);
    expect(read.segmented.target.syncRoot, isNot(b.serverStateFingerprint));
    for (final e in before.entries) {
      expect(File(e.key).readAsBytesSync(), e.value);
    }
    expect(state.isOffline, true);
    expect(requests, 0);
  });
  test('finalizing and recovery-blocked modes have no adapter bypass',
      () async {
    for (final mode in [
      ConnectivityMode.reconciliationFinalizing,
      ConnectivityMode.persistenceRecoveryBlocked
    ]) {
      state.connectivityMode = mode;
      await expectLater(state.readSegmentedForIsolatedUse(store),
          throwsA(isA<SegmentedException>()));
    }
  });

  test('actual financial mutation invalidates waiting original read ticket',
      () async {
    offline.pause();
    final waiting =
        state.readSegmentedForIsolatedUse(store, includePending: true);
    await offline.entered!.future;
    await state.updateSetting('owner_card_last4', '1234');
    offline.release!.complete();
    await expectLater(waiting, throwsA(isA<Exception>()));
    expect(requests, 1);
    persisted();
  });

  test(
      'pending append during read uses existing journal serialization and stable snapshot',
      () async {
    final b = baselineFixture();
    await offline.replaceBaseline(b);
    await offline.saveMetadata(OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint: offline.recoveryLineageFingerprint(b)));
    state.connectivityMode = ConnectivityMode.offline;
    Future<void> append(int n) async {
      await offline.appendOperation(
          type: OfflineOperationType.createCashFlow,
          payload: {
            'occurred_on': '2026-10-14',
            'title': '합성 $n',
            'amount_value': n,
            'is_primary_income': 0
          },
          baseline: b);
    }

    await append(1);
    offline.pause();
    final waiting =
        state.readSegmentedForIsolatedUse(store, includePending: true);
    await offline.entered!.future;
    await append(2);
    offline.release!.complete();
    final read = await waiting;
    expect(
        read.pendingLegacy!.bundle.operations.map((o) => o.sequence), [1, 2]);
    await append(3);
    expect(read.pendingLegacy!.bundle.operations.length, 2);
    expect((await offline.loadJournal()).map((o) => o.sequence), [1, 2, 3]);
    persisted();
  });
}
