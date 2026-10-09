import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'support/offline_mode_fixtures.dart';

class DelayedRefreshApiFake extends OfflineApiFake {
  final summaryRequested = Completer<void>();
  final releaseSummary = Completer<void>();

  @override
  Future<Summary> summary() async {
    if (!summaryRequested.isCompleted) summaryRequested.complete();
    await releaseSummary.future;
    return super.summary();
  }
}

class ChangingBaselineApiFake extends OfflineApiFake {
  int baselineCalls = 0;

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async {
    baselineCalls += 1;
    final fingerprint = baselineCalls == 1
        ? baselineFixture().serverStateFingerprint
        : OfflineApiFake.currentFingerprint;
    if (baselineCalls == 2) remainingLiquidity = 9000;
    return {
      'snapshot': const {
        'schema_version': 2,
        'exported_at': '2026-09-17T03:14:00Z',
        'data': <String, dynamic>{},
      },
      'state_fingerprint': fingerprint,
      'state_revision': baselineCalls == 1 ? 1 : 2,
      'evaluation_date': '2026-09-17',
      'discount_policy_defaults': const {
        'owner': 'enabled',
        'family': 'disabled'
      },
    };
  }
}

class AbaRefreshApiFake extends OfflineApiFake {
  int envelopeCalls = 0;
  bool changeEvaluationDate = false;

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async {
    envelopeCalls += 1;
    final result = await super.offlineReconciliationBaseline();
    if (envelopeCalls == 1) remainingLiquidity = 101234;
    if (envelopeCalls == 2) remainingLiquidity = 100000;
    return {
      ...result,
      'state_revision': envelopeCalls == 1 ? 1 : 3,
      'evaluation_date': changeEvaluationDate && envelopeCalls > 1
          ? '2026-09-18'
          : '2026-09-17',
    };
  }
}

class OverlappingRefreshApiFake extends OfflineApiFake {
  final firstRequested = Completer<void>();
  final secondRequested = Completer<void>();
  final firstResult = Completer<Summary>();
  final secondResult = Completer<Summary>();
  int summaryCalls = 0;

  @override
  Future<Summary> summary() {
    summaryCalls += 1;
    if (summaryCalls == 1) {
      firstRequested.complete();
      return firstResult.future;
    }
    secondRequested.complete();
    return secondResult.future;
  }
}

class DelayedMutationApiFake extends OfflineApiFake {
  final cashCreateRequested = Completer<void>();
  final cashCreateResult = Completer<CashFlow>();
  int cashCreateCalls = 0;

  @override
  Future<CashFlow> createCashFlow({
    required String occurredOn,
    required String title,
    required int amount,
    required bool isPrimaryIncome,
  }) {
    cashCreateCalls += 1;
    if (!cashCreateRequested.isCompleted) cashCreateRequested.complete();
    return cashCreateResult.future;
  }
}

class ScriptedRecoveryApiFake extends OfflineApiFake {
  ScriptedRecoveryApiFake(this.probeResults);

  List<bool> probeResults;

  @override
  Future<void> health({Duration timeout = const Duration(seconds: 15)}) async {
    healthCalls += 1;
    final succeeds =
        probeResults.isEmpty ? available : probeResults.removeAt(0);
    if (!succeeds) {
      onServerUnavailable?.call();
      throw MoneyNoteConnectionException('일시적 연결 실패');
    }
  }
}

class OneFailedRefreshApiFake extends ScriptedRecoveryApiFake {
  OneFailedRefreshApiFake() : super([true, true]);

  bool failNextSummary = true;

  @override
  Future<Summary> summary() async {
    if (failNextSummary) {
      failNextSummary = false;
      onServerUnavailable?.call();
      throw MoneyNoteConnectionException('요약 요청 시간 초과');
    }
    return super.summary();
  }
}

class PausedRecoveryApiFake extends ScriptedRecoveryApiFake {
  PausedRecoveryApiFake() : super([true]);

  final probeStarted = Completer<void>();
  final resumeProbe = Completer<void>();

  @override
  Future<void> health({Duration timeout = const Duration(seconds: 15)}) async {
    probeStarted.complete();
    await resumeProbe.future;
    await super.health(timeout: timeout);
  }

  @override
  Future<void> logout() async {}
}

class FailedLogoutApiFake extends ScriptedRecoveryApiFake {
  FailedLogoutApiFake() : super([true]);

  @override
  Future<void> logout() async {
    onServerUnavailable?.call();
    throw MoneyNoteConnectionException('logout response lost');
  }
}

class FailingRefreshBaselineStore extends OfflineStore {
  FailingRefreshBaselineStore(Directory directory)
      : super(directoryProvider: () async => directory);

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    throw const OfflinePersistenceException(
        'injected baseline install failure');
  }
}

class PausedRefreshBaselineStore extends OfflineStore {
  PausedRefreshBaselineStore(Directory directory)
      : super(directoryProvider: () async => directory);

  final saving = Completer<void>();
  final release = Completer<void>();

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    saving.complete();
    await release.future;
    await super.replaceBaseline(baseline, beforePublish: beforePublish);
  }
}

class PausedBaselineTemporaryFile implements File {
  PausedBaselineTemporaryFile(this.delegate, this.flushed, this.release);

  final File delegate;
  final Completer<void> flushed;
  final Completer<void> release;

  @override
  String get path => delegate.path;

  @override
  Future<File> writeAsString(String value,
      {FileMode mode = FileMode.write,
      Encoding encoding = utf8,
      bool flush = false}) async {
    await delegate.writeAsString(value,
        mode: mode, encoding: encoding, flush: true);
    flushed.complete();
    await release.future;
    return delegate;
  }

  @override
  Future<String> readAsString({Encoding encoding = utf8}) =>
      delegate.readAsString(encoding: encoding);

  @override
  File renameSync(String newPath) => delegate.renameSync(newPath);

  @override
  Future<bool> exists() => delegate.exists();

  @override
  Future<FileSystemEntity> delete({bool recursive = false}) =>
      delegate.delete(recursive: recursive);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class SessionRefreshApiFake extends OfflineApiFake {
  final firstSummaryRequested = Completer<void>();
  final firstSummaryResult = Completer<Summary>();
  bool delayFirstSummary = false;
  int summaryCalls = 0;

  @override
  Future<Summary> summary() async {
    summaryCalls += 1;
    if (delayFirstSummary && summaryCalls == 1) {
      firstSummaryRequested.complete();
      return firstSummaryResult.future;
    }
    return super.summary();
  }

  @override
  Future<void> logout() async {}

  @override
  Future<AuthUser> login(String username, String password) async {
    principalId = 2;
    return AuthUser(
      id: 2,
      username: username,
      displayName: 'New session',
      sharePinNeedsChange: false,
    );
  }

  @override
  Future<SnapshotDownload> downloadSnapshot() async =>
      throw StateError('skip unrelated launch backup');
}

class PausedLogoutApiFake extends SessionRefreshApiFake {
  final logoutStarted = Completer<void>();
  final finishLogout = Completer<void>();

  @override
  Future<void> logout() async {
    logoutStarted.complete();
    await finishLogout.future;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('transient connection recovery', () {
    Future<AppState> onlineState(ScriptedRecoveryApiFake api) async {
      return AppState(api,
          offlineStore: offlineStoreFixture(await temporaryDirectoryFixture()),
          connectivityRetryDelay: (_) async {})
        ..user = baselineFixture().user
        ..isBootstrapping = false;
    }

    test(
        'one failed request does not immediately replace the app with an offline offer',
        () async {
      final api = OfflineApiFake()..available = true;
      final state = AppState(api,
          offlineStore: offlineStoreFixture(await temporaryDirectoryFixture()))
        ..user = baselineFixture().user
        ..isBootstrapping = false;

      api.onServerUnavailable!.call();

      expect(state.networkUnavailable, isTrue);
      expect(state.serverFailurePromptPending, isFalse);
    });

    test('one transient failure recovers with a coherent refresh', () async {
      final api = ScriptedRecoveryApiFake([true])..available = true;
      final state = await onlineState(api);

      api.onServerUnavailable!.call();
      await state.recoverConnectivity();

      expect(api.healthCalls, 1);
      expect(state.summary, isNotNull);
      expect(state.networkUnavailable, isFalse);
      expect(state.serverFailurePromptPending, isFalse);
    });

    test('later bounded probe success suppresses the offline offer', () async {
      final api = ScriptedRecoveryApiFake([false, false, true])
        ..available = true;
      final state = await onlineState(api);

      api.onServerUnavailable!.call();
      await state.recoverConnectivity();

      expect(api.healthCalls, 3);
      expect(state.summary, isNotNull);
      expect(state.serverFailurePromptPending, isFalse);
    });

    test('healthy server with one timed-out constituent read retries refresh',
        () async {
      final api = OneFailedRefreshApiFake()..available = true;
      final state = await onlineState(api);

      api.onServerUnavailable!.call();
      await state.recoverConnectivity();

      expect(api.healthCalls, 2);
      expect(state.summary, isNotNull);
      expect(state.serverFailurePromptPending, isFalse);
    });

    test('logout revokes a paused connectivity recovery installation',
        () async {
      final api = PausedRecoveryApiFake()..available = true;
      final state = await onlineState(api);
      api.onServerUnavailable!.call();
      final recovery = state.recoverConnectivity();
      await api.probeStarted.future;

      await state.logout();
      api.resumeProbe.complete();
      await recovery;

      expect(state.isLoggedIn, isFalse);
      expect(state.summary, isNull);
      expect(state.serverFailurePromptPending, isFalse);
    });

    test('failed logout cannot leave old user visible to later recovery',
        () async {
      final api = FailedLogoutApiFake()..available = true;
      final state = await onlineState(api);
      state.summary = baselineFixture().summary;

      await state.logout();
      await state.recoverConnectivity();

      expect(state.user, isNull);
      expect(state.summary, isNull);
      expect(state.networkUnavailable, isFalse);
      expect(state.serverFailurePromptPending, isFalse);
    });

    test('bounded probe failure eventually offers offline mode', () async {
      final api = ScriptedRecoveryApiFake([false, false, false]);
      final state = await onlineState(api);

      api.onServerUnavailable!.call();
      expect(state.serverFailurePromptPending, isFalse);
      await state.recoverConnectivity();

      expect(api.healthCalls, 3);
      expect(state.networkUnavailable, isTrue);
      expect(state.serverFailurePromptPending, isTrue);
    });

    test('foreground retries a visible offer and clears it when reachable',
        () async {
      final api = ScriptedRecoveryApiFake([false, false, false])
        ..available = true;
      final state = await onlineState(api);
      api.onServerUnavailable!.call();
      await state.recoverConnectivity();
      expect(state.serverFailurePromptPending, isTrue);

      api.probeResults = [true];
      await state.resumeFromBackground();

      expect(api.healthCalls, 4);
      expect(state.serverFailurePromptPending, isFalse);
      expect(state.networkUnavailable, isFalse);
      expect(state.isOnline, isTrue);
    });

    test('foreground preserves the offer when the server still fails',
        () async {
      final api = ScriptedRecoveryApiFake([false, false, false]);
      final state = await onlineState(api);
      api.onServerUnavailable!.call();
      await state.recoverConnectivity();

      api.probeResults = [false, false, false];
      await state.resumeFromBackground();

      expect(api.healthCalls, 6);
      expect(state.serverFailurePromptPending, isTrue);
    });

    test('explicit offline choice does not silently become online on resume',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final api = ScriptedRecoveryApiFake([true])..available = true;
      final state = AppState(api,
          offlineStore: store, connectivityRetryDelay: (_) async {})
        ..user = baselineFixture().user
        ..isBootstrapping = false;
      expect(await state.enterOfflineMode(), isTrue);

      await state.resumeFromBackground();

      expect(state.isOnline, isFalse);
      expect(state.isReconciliationRequired, isTrue);
      expect(state.serverFailurePromptPending, isFalse);
    });

    test(
        'foreground refresh clears a stale offline offer when the server is healthy',
        () async {
      final api = OfflineApiFake()..available = true;
      final state = AppState(api,
          offlineStore: offlineStoreFixture(await temporaryDirectoryFixture()))
        ..user = baselineFixture().user
        ..isBootstrapping = false
        ..networkUnavailable = true
        ..serverFailurePromptPending = true;

      await state.resumeFromBackground();

      expect(state.isOnline, isTrue);
      expect(state.networkUnavailable, isFalse);
      expect(state.serverFailurePromptPending, isFalse);
      expect(state.summary, isNotNull);
    });
  });

  group('online refresh baseline and connection classification', () {
    test('logout during baseline write prevents stale disk and UI install',
        () async {
      final directory = await temporaryDirectoryFixture();
      final seeded = offlineStoreFixture(directory);
      await seeded.replaceBaseline(baselineFixture(remainingLiquidity: 100000));
      final store = PausedRefreshBaselineStore(directory);
      final api = SessionRefreshApiFake()
        ..available = true
        ..remainingLiquidity = 99500;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;

      final pending = state.refresh();
      final rejection =
          expectLater(pending, throwsA(isA<MoneyNoteApiException>()));
      await store.saving.future;
      await state.logout();
      expect(state.isLoggedIn, isFalse);
      store.release.complete();
      await rejection;
      expect(state.user, isNull);
      expect(state.summary, isNull);
      expect((await seeded.loadBaseline())!.summary.remainingLiquidity, 100000);
    });

    test('logout after temporary baseline flush cancels final publication',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 100000));
      final api = SessionRefreshApiFake()
        ..available = true
        ..remainingLiquidity = 99500;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;
      final flushed = Completer<void>();
      final release = Completer<void>();
      final parentZone = Zone.current;
      final pending =
          IOOverrides.runZoned(() => state.refresh(), createFile: (path) {
        final real = parentZone.run(() => File(path));
        return path.startsWith(directory.path) && path.endsWith('.tmp')
            ? PausedBaselineTemporaryFile(real, flushed, release)
            : real;
      });
      final rejection =
          expectLater(pending, throwsA(isA<MoneyNoteApiException>()));
      await flushed.future;
      await state.logout();
      release.complete();
      await rejection;
      expect(state.isLoggedIn, isFalse);
      expect(state.summary, isNull);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 100000);
    });

    test('logout invalidates a late network refresh', () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 100000));
      final api = SessionRefreshApiFake()
        ..available = true
        ..delayFirstSummary = true;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;

      final pending = state.refresh();
      final rejection =
          expectLater(pending, throwsA(isA<MoneyNoteApiException>()));
      await api.firstSummaryRequested.future;
      await state.logout();
      api.firstSummaryResult.complete(baselineFixture().summary);
      await rejection;
      expect(state.isLoggedIn, isFalse);
      expect(state.summary, isNull);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 100000);
    });

    test('refresh started during logout cannot install after logout completes',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 100000));
      final api = PausedLogoutApiFake()
        ..available = true
        ..delayFirstSummary = true;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;

      final loggingOut = state.logout();
      await api.logoutStarted.future;
      final pending = state.refresh();
      final rejection =
          expectLater(pending, throwsA(isA<MoneyNoteApiException>()));
      await api.firstSummaryRequested.future;
      api.finishLogout.complete();
      await loggingOut;
      api.firstSummaryResult.complete(baselineFixture().summary);
      await rejection;
      expect(state.isLoggedIn, isFalse);
      expect(state.summary, isNull);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 100000);
    });

    test('late old-session response cannot overwrite a new login refresh',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final api = SessionRefreshApiFake()
        ..available = true
        ..delayFirstSummary = true;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;

      final oldRefresh = state.refresh();
      final rejection =
          expectLater(oldRefresh, throwsA(isA<MoneyNoteApiException>()));
      await api.firstSummaryRequested.future;
      await state.logout();
      api.remainingLiquidity = 99500;
      await state.login('new-owner', 'test-password');
      expect(state.user!.username, 'new-owner');
      expect(state.summary!.remainingLiquidity, 99500);
      api.firstSummaryResult
          .complete(baselineFixture(remainingLiquidity: 100000).summary);
      await rejection;
      expect(state.user!.username, 'new-owner');
      expect(state.summary!.remainingLiquidity, 99500);
      expect((await store.loadBaseline())!.user.username, 'new-owner');
    });

    test('baseline persistence must finish before fresh UI state is installed',
        () async {
      final directory = await temporaryDirectoryFixture();
      final seeded = offlineStoreFixture(directory);
      await seeded.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      final api = OfflineApiFake()
        ..available = true
        ..remainingLiquidity = 9000;
      final state =
          AppState(api, offlineStore: FailingRefreshBaselineStore(directory))
            ..user = baselineFixture().user;

      await expectLater(
          state.refresh(), throwsA(isA<OfflinePersistenceException>()));
      expect(state.summary, isNull);
      expect((await seeded.loadBaseline())!.summary.remainingLiquidity, 10000);
    });

    test(
        'successful refresh replaces baseline; incomplete refresh preserves it',
        () async {
      final directory = await temporaryDirectoryFixture();
      final api = OfflineApiFake()..available = true;
      final store = offlineStoreFixture(directory);
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;

      await state.refresh();
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 10000);

      api.remainingLiquidity = 9000;
      await state.refresh();
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 9000);

      api.remainingLiquidity = 8000;
      api.failJudgment = true;
      await expectLater(state.refresh(), throwsStateError);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 9000);
    });

    test('transport failure prompts, but application validation error does not',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final unavailableClient = MockClient((request) async {
        throw http.ClientException('offline', request.url);
      });
      final unavailableApi = MoneyNoteApiClient(
        client: unavailableClient,
        baseUrl: 'https://example.invalid',
      );
      final unavailableState = AppState(unavailableApi, offlineStore: store);
      await expectLater(
        unavailableApi.summary(),
        throwsA(isA<MoneyNoteConnectionException>()),
      );
      expect(unavailableState.serverFailurePromptPending, isFalse);
      await unavailableState.recoverConnectivity();
      expect(unavailableState.serverFailurePromptPending, isTrue);
      expect(await unavailableState.enterOfflineMode(), isTrue);
      expect(unavailableState.isOffline, isTrue);

      final validationApi = MoneyNoteApiClient(
        client: MockClient((request) async => http.Response(
              jsonEncode({'detail': 'invalid amount'}),
              422,
              headers: {'content-type': 'application/json'},
            )),
        baseUrl: 'https://example.invalid',
      );
      final validationState = AppState(validationApi);
      await expectLater(
        validationApi.summary(),
        throwsA(isA<MoneyNoteApiException>()),
      );
      expect(validationState.serverFailurePromptPending, isFalse);
    });
    test('late ONLINE refresh cannot replace a frozen Offline lineage',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      final api = DelayedRefreshApiFake()..available = true;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;

      final delayedRefresh = state.refresh();
      await api.summaryRequested.future;
      expect(await state.enterOfflineMode(), isTrue);
      expect(
        await state.createCashFlow(
          occurredOn: '2026-09-17',
          title: '오프라인 출금',
          amount: 500,
          isIncome: false,
          isPrimaryIncome: false,
        ),
        isTrue,
      );
      api.remainingLiquidity = 11234;
      api.releaseSummary.complete();

      await expectLater(delayedRefresh, throwsA(isA<MoneyNoteApiException>()));
      expect(state.isOffline, isTrue);
      expect(state.summary!.remainingLiquidity, 9500);
      expect(
        (await store.loadBaseline())!.summary.remainingLiquidity,
        10000,
      );
      expect(await store.loadJournal(), hasLength(1));
    });

    test('mixed display and Snapshot generations are rejected and retried',
        () async {
      final directory = await temporaryDirectoryFixture();
      final api = ChangingBaselineApiFake()..available = true;
      final store = offlineStoreFixture(directory);
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;

      await state.refresh();

      expect(api.baselineCalls, 4);
      expect(state.summary!.remainingLiquidity, 9000);
      final installed = await store.loadBaseline();
      expect(installed!.summary.remainingLiquidity, 9000);
      expect(installed.serverStateFingerprint, api.bundleFingerprint);
    });
    test('A-B-A with equal fingerprint rejects middle display by revision',
        () async {
      final directory = await temporaryDirectoryFixture();
      final api = AbaRefreshApiFake()..available = true;
      final store = offlineStoreFixture(directory);
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;
      await state.refresh();
      expect(api.envelopeCalls, 4);
      expect(state.summary!.remainingLiquidity, 100000);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 100000);
    });

    test('evaluation date change rejects stale display even without DB change',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      final api = AbaRefreshApiFake()
        ..available = true
        ..changeEvaluationDate = true;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;
      await expectLater(state.refresh(), throwsA(isA<MoneyNoteApiException>()));
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 10000);
    });

    test('newer ONLINE refresh wins when its response completes first',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final api = OverlappingRefreshApiFake()..available = true;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;
      final first = state.refresh();
      await api.firstRequested.future;
      final second = state.refresh();
      await api.secondRequested.future;
      api.secondResult
          .complete(baselineFixture(remainingLiquidity: 101234).summary);
      await second;
      api.firstResult
          .complete(baselineFixture(remainingLiquidity: 100000).summary);
      await expectLater(first, throwsA(isA<MoneyNoteApiException>()));
      expect(state.summary!.remainingLiquidity, 101234);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 101234);
    });

    test('newer ONLINE refresh wins when older response completes first',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final api = OverlappingRefreshApiFake()..available = true;
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user;
      final first = state.refresh();
      await api.firstRequested.future;
      final second = state.refresh();
      await api.secondRequested.future;
      api.firstResult
          .complete(baselineFixture(remainingLiquidity: 100000).summary);
      await expectLater(first, throwsA(isA<MoneyNoteApiException>()));
      api.secondResult
          .complete(baselineFixture(remainingLiquidity: 101234).summary);
      await second;
      expect(state.summary!.remainingLiquidity, 101234);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 101234);
    });
    test('AppState mutation single-flight rejects concurrent re-entry',
        () async {
      final directory = await temporaryDirectoryFixture();
      final api = DelayedMutationApiFake()..available = true;
      final state = AppState(api, offlineStore: offlineStoreFixture(directory))
        ..user = baselineFixture().user;

      final first = state.createCashFlow(
        occurredOn: '2026-09-17',
        title: '한 번만 저장',
        amount: 500,
        isIncome: true,
        isPrimaryIncome: false,
      );
      await api.cashCreateRequested.future;
      final duplicate = await state.createCashFlow(
        occurredOn: '2026-09-17',
        title: '중복 진입',
        amount: 500,
        isIncome: true,
        isPrimaryIncome: false,
      );
      expect(duplicate, isFalse);
      expect(api.cashCreateCalls, 1);

      api.cashCreateResult.complete(CashFlow(
        id: 1,
        occurredOn: '2026-09-17',
        title: '한 번만 저장',
        amountValue: 500,
        sortOrder: 1,
        isPrimaryIncome: false,
      ));
      expect(await first, isTrue);
      expect(api.cashCreateCalls, 1);
    });

    test('offline append failure leaves journal and projection unchanged',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = OfflineStore(
        directoryProvider: () async => directory,
        beforeJournalAppendWrite: () async {
          throw const OfflinePersistenceException(
              'injected journal disk failure');
        },
      );
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      await saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.offline,
          ));
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);

      expect(
        await state.createCashFlow(
          occurredOn: '2026-09-17',
          title: '기록되면 안 됨',
          amount: 500,
          isIncome: false,
          isPrimaryIncome: false,
        ),
        isFalse,
      );

      expect(state.isOffline, isTrue);
      expect(state.offlineJournal, isEmpty);
      expect(state.summary!.remainingLiquidity, 10000);
      expect(await store.loadJournal(), isEmpty);
    });
  });
}
