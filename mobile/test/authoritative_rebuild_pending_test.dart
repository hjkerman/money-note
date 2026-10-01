import 'dart:io';
import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/offline/online_write_state.dart';
import 'support/offline_mode_fixtures.dart';

class PublicationFailureStore extends OfflineStore {
  PublicationFailureStore(Directory d)
      : super(directoryProvider: () async => d);
  bool fail = false;
  bool failCleanup = false;
  bool failMarker = false;
  @override
  Future<void> savePendingOnlineWrite(PendingOnlineWrite pending) async {
    if (failMarker) throw const OfflinePersistenceException('marker failed');
    await super.savePendingOnlineWrite(pending);
  }

  @override
  Future<void> completeOnlineWrite(PendingOnlineWrite pending) async {
    if (failCleanup) {
      throw const OfflinePersistenceException('marker cleanup failed');
    }
    await super.completeOnlineWrite(pending);
  }

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    if (fail) throw const OfflinePersistenceException('publication failed');
    await super.replaceBaseline(baseline, beforePublish: beforePublish);
  }
}

class CommittingApi extends OfflineApiFake {
  int writes = 0;
  int panelWrites = 0;
  @override
  Future<MonthlyPanel> createPanel(
      {required String month,
      required String panelType,
      required String title,
      required int amount,
      String? spentOn,
      String? candidateRegistrationKey,
      bool? initialDiscountEnabled}) async {
    panelWrites++;
    return MonthlyPanel(
        id: 1,
        month: month,
        panelType: panelType,
        discountAmount: 0,
        discountOverride: 0,
        title: title,
        sortOrder: 1,
        amountValue: amount);
  }

  bool loseResponse = false;
  bool rejectWrite = false;
  int rejectionStatus = 422;
  bool loseRequest = false;
  Completer<void>? readStarted;
  Completer<void>? releaseRead;
  @override
  Future<Summary> summary() async {
    final result = await super.summary();
    final started = readStarted;
    final release = releaseRead;
    readStarted = null;
    releaseRead = null;
    started?.complete();
    if (release != null) await release.future;
    return result;
  }

  @override
  Future<void> logout() async {}
  @override
  Future<AuthUser> login(String username, String password) async {
    remainingLiquidity = 7000;
    return AuthUser(
        id: 2,
        username: username,
        displayName: username,
        sharePinNeedsChange: false);
  }

  @override
  Future<SnapshotDownload> downloadSnapshot() async =>
      throw StateError('no maintenance snapshot in test');
  @override
  Future<CashFlow> createCashFlow(
      {required String occurredOn,
      required String title,
      required int amount,
      required bool isPrimaryIncome}) async {
    if (rejectWrite) {
      throw MoneyNoteApiException('request rejected',
          statusCode: rejectionStatus);
    }
    if (loseRequest) {
      throw MoneyNoteConnectionException('request lost before server');
    }
    writes++;
    remainingLiquidity += amount;
    if (loseResponse) {
      throw MoneyNoteConnectionException('commit succeeded / response lost');
    }
    return CashFlow(
        id: writes,
        occurredOn: occurredOn,
        title: title,
        amountValue: amount,
        sortOrder: 1,
        isPrimaryIncome: isPrimaryIncome);
  }

  @override
  Future<LedgerEntry> createExpense(
      {required String date,
      required String usagePlace,
      required String usageItem,
      required int amount,
      required bool discountEnabled,
      int? discountOverrideAmount,
      String? spendingCategory,
      String? candidateRegistrationKey}) async {
    writes++;
    remainingLiquidity -= amount;
    return LedgerEntry(
        id: writes,
        bookSection: 'current',
        entryKind: 'expense',
        title: usageItem,
        sortOrder: 1,
        entryDate: date,
        usagePlace: usagePlace,
        amountValue: amount);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final cash in [true, false]) {
    test(
        'committed ${cash ? 'cash' : 'card'} cannot succeed or start stale Offline after publication failure',
        () async {
      final dir = await Directory.systemTemp.createTemp('closure-rebuild-');
      addTearDown(() => dir.delete(recursive: true));
      final api = CommittingApi();
      final store = PublicationFailureStore(dir);
      final state = AppState(api, offlineStore: store)
        ..user = baselineFixture().user
        ..isBootstrapping = false;
      addTearDown(state.dispose);
      await state.refreshInputArea(notify: false);
      store.fail = true;
      final saved = cash
          ? await state.createCashFlow(
              occurredOn: '2026-09-17',
              title: 'fact',
              amount: 500,
              isIncome: false,
              isPrimaryIncome: false)
          : await state.createExpense(
              usagePlace: 'shop',
              usageItem: 'fact',
              amount: 500,
              discountEnabled: true);
      expect(saved, isFalse);
      expect(state.lastSubmitServerCommitted, isTrue);
      expect(state.onlineWriteStatus,
          OnlineWriteStatus.serverCommittedRebuildPending);
      expect(api.writes, 1);
      expect(await state.enterOfflineMode(), isFalse);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 10000);
      store.fail = false;
      await state.refreshInputArea(notify: false);
      expect(api.writes, 1);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 9500);
      expect(await state.enterOfflineMode(), isTrue);
    });
  }

  Future<(AppState, CommittingApi, PublicationFailureStore, Directory)>
      fixture() async {
    final dir =
        await Directory.systemTemp.createTemp('closure-rebuild-sibling-');
    addTearDown(() => dir.delete(recursive: true));
    final api = CommittingApi()..available = true;
    final store = PublicationFailureStore(dir);
    final state =
        AppState(api, offlineStore: store, connectivityRetryDelay: (_) async {})
          ..user = baselineFixture().user
          ..isBootstrapping = false;
    addTearDown(state.dispose);
    await state.refreshInputArea(notify: false);
    return (state, api, store, dir);
  }

  Future<bool> submit(AppState state) => state.createCashFlow(
      occurredOn: '2026-09-17',
      title: 'fact',
      amount: 500,
      isIncome: false,
      isPrimaryIncome: false);

  test(
      'committed refresh failure survives restart, blocks repeat and recovers on foreground read only',
      () async {
    final (state, api, store, _) = await fixture();
    api.failJudgment = true;
    expect(await submit(state), isFalse);
    expect(await submit(state), isFalse);
    expect(api.writes, 1);
    final restarted = AppState(api, offlineStore: store)
      ..isBootstrapping = false;
    addTearDown(restarted.dispose);
    expect(await restarted.restorePersistedOfflineWorkspace(), isFalse);
    restarted.user = baselineFixture().user;
    expect(restarted.onlineWriteStatus,
        OnlineWriteStatus.serverCommittedRebuildPending);
    expect(await restarted.enterOfflineMode(), isFalse);
    api.failJudgment = false;
    await restarted.resumeFromBackground();
    expect(restarted.authoritativeRebuildPending, isFalse);
    expect(restarted.summary!.remainingLiquidity, 9500);
    expect(api.writes, 1);
    expect(await restarted.enterOfflineMode(), isTrue);
  });

  test(
      'cleanup failure keeps fresh published baseline gated until later read-only rebuild',
      () async {
    final (state, api, store, _) = await fixture();
    store.failCleanup = true;
    expect(await submit(state), isFalse);
    expect(state.summary!.remainingLiquidity, 10000);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 9500);
    expect(await state.enterOfflineMode(), isFalse);
    store.failCleanup = false;
    expect(await state.rebuildAfterOnlineWrite(), isTrue);
    expect(api.writes, 1);
    expect(state.summary!.remainingLiquidity, 9500);
  });

  test(
      'pre-request marker failure prevents HTTP; definite 422 retires only first attempt marker',
      () async {
    final (state, api, store, _) = await fixture();
    store.failMarker = true;
    expect(await submit(state), isFalse);
    expect(api.writes, 0);
    expect(await store.loadPendingOnlineWrite(1), isNull);
    store.failMarker = false;
    api.rejectWrite = true;
    expect(await submit(state), isFalse);
    expect(await store.loadPendingOnlineWrite(1), isNull);
    api.rejectWrite = false;
    expect(await submit(state), isTrue);
    expect(api.writes, 1);
  });

  for (final reachedServer in [false, true]) {
    test(
        'ambiguous ${reachedServer ? "response" : "request"} loss never blindly replays or allows Offline',
        () async {
      final (state, api, store, _) = await fixture();
      api.loseResponse = reachedServer;
      api.loseRequest = !reachedServer;
      expect(await submit(state), isFalse);
      expect(state.onlineWriteStatus, OnlineWriteStatus.outcomeUnknown);
      expect(await submit(state), isFalse);
      expect(api.writes, reachedServer ? 1 : 0);
      expect(await state.rebuildAfterOnlineWrite(), isFalse);
      expect(await state.enterOfflineMode(), isFalse);
      expect(await store.loadPendingOnlineWrite(1), isNotNull);
      expect(api.writes, reachedServer ? 1 : 0);
    });
  }

  test(
      'pre-write authentication rejection does not create a permanent unknown outcome',
      () async {
    final (state, api, store, _) = await fixture();
    api.rejectWrite = true;
    api.rejectionStatus = 401;
    expect(await submit(state), isFalse);
    expect(api.writes, 0);
    expect(await store.loadPendingOnlineWrite(1), isNull);
    expect(state.authoritativeRebuildPending, isFalse);
    api.rejectWrite = false; // authentication has been recovered
    expect(await submit(state), isTrue);
    expect(api.writes, 1);
  });

  test(
      'logout and new login revoke a late pending rebuild without clearing old user marker',
      () async {
    final (state, api, store, _) = await fixture();
    store.fail = true;
    expect(await submit(state), isFalse);
    store.fail = false;
    final started = api.readStarted = Completer<void>();
    final release = api.releaseRead = Completer<void>();
    final old = state.refreshInputArea(notify: false);
    final rejectedOld = expectLater(old, throwsA(isA<MoneyNoteApiException>()));
    await started.future;
    await state.logout();
    expect(await store.loadPendingOnlineWrite(1), isNotNull);
    await state.login('new-owner', 'test');
    release.complete();
    await rejectedOld;
    expect(state.user!.id, 2);
    expect(state.summary!.remainingLiquidity, 7000);
    expect((await store.loadBaseline())!.user.id, 2);
    expect(await store.loadPendingOnlineWrite(1), isNotNull);
    expect(await store.loadPendingOnlineWrite(2), isNull);
    expect(api.writes, 1);
  });

  test(
      'unrelated idempotent panel retry cannot retire an ambiguous cash write marker',
      () async {
    final (state, api, store, _) = await fixture();
    await store.reserveManualPanelRetryKey({
      'month': '2026-09',
      'panel_type': 'claim',
      'title': 'old panel',
      'spent_on': '2026-09-17',
      'amount_value': 100,
      'discount_enabled': true,
    }, preferredKey: 'old-panel-identity');
    api.loseResponse = true;
    expect(await submit(state), isFalse);
    final marker = await store.loadPendingOnlineWrite(1);
    expect(await state.confirmPendingManualPanelRegistration(), isFalse);
    expect(api.panelWrites, 0);
    expect((await store.loadPendingOnlineWrite(1))!.token, marker!.token);
    expect(state.onlineWriteStatus, OnlineWriteStatus.outcomeUnknown);
    expect(await state.enterOfflineMode(), isFalse);
  });

  test(
      'pending online mutation and persisted Offline lineage fail closed without replay',
      () async {
    final (state, api, store, _) = await fixture();
    store.fail = true;
    expect(await submit(state), isFalse);
    final baseline = (await store.loadBaseline())!;
    await store.saveMetadata(OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint:
            store.recoveryLineageFingerprint(baseline)));
    final restarted = AppState(api, offlineStore: store);
    addTearDown(restarted.dispose);
    expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);
    expect(restarted.isPersistenceRecoveryBlocked, isTrue);
    expect(api.writes, 1);
    expect(await store.loadPendingOnlineWrite(1), isNotNull);
  });
}
