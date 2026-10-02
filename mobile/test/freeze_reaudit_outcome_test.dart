import 'dart:io';
import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/mutation_contract.dart';
import 'authoritative_rebuild_pending_test.dart' show CommittingApi;
import 'support/offline_mode_fixtures.dart';

class OutcomeApi extends CommittingApi {
  int deleteStatus = 404;
  int ownerId = 1;
  bool panelResponseLoss = false;
  final Set<String?> registered = {};
  int panelAttempts = 0;
  @override
  Future<void> deleteEntry(int id) async {
    if (deleteStatus == 0) throw MoneyNoteConnectionException('response lost');
    throw MoneyNoteApiException('delete rejected', statusCode: deleteStatus);
  }

  @override
  Future<AuthUser> login(String username, String password) async => AuthUser(
      id: ownerId,
      username: username,
      displayName: username,
      sharePinNeedsChange: false);
  @override
  Future<MonthlyPanel> createPanel(
      {required String month,
      required String panelType,
      required String title,
      required int amount,
      String? spentOn,
      String? candidateRegistrationKey,
      bool? initialDiscountEnabled}) async {
    panelAttempts++;
    if (registered.add(candidateRegistrationKey)) panelWrites++;
    if (panelResponseLoss) {
      throw MoneyNoteConnectionException('committed response lost');
    }
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
}

class GatedOwnerStore extends OfflineStore {
  GatedOwnerStore(this.directory)
      : super(directoryProvider: () async => directory);
  final Directory directory;
  Completer<void>? ownerChecked;
  Completer<void>? releaseOwner;
  @override
  Future<void> requireManualPanelRetryOwner(
      PendingManualPanelRetry pending, int ownerId) async {
    await super.requireManualPanelRetryOwner(pending, ownerId);
    final checked = ownerChecked;
    final release = releaseOwner;
    ownerChecked = null;
    releaseOwner = null;
    checked?.complete();
    if (release != null) await release.future;
  }
}

void main() {
  Future<(AppState, OutcomeApi, OfflineStore)> fixture(
      {bool gated = false}) async {
    final dir = await Directory.systemTemp.createTemp('reaudit-outcomes-');
    addTearDown(() => dir.delete(recursive: true));
    final api = OutcomeApi()..available = true;
    final store = gated
        ? GatedOwnerStore(dir)
        : OfflineStore(directoryProvider: () async => dir);
    final state =
        AppState(api, offlineStore: store, connectivityRetryDelay: (_) async {})
          ..user = baselineFixture().user
          ..isBootstrapping = false;
    addTearDown(state.dispose);
    await state.refreshInputArea(notify: false);
    return (state, api, store);
  }

  test('outcome contracts are endpoint specific, not global HTTP allowlists',
      () {
    expect(
        MutationContract.validatedWrite.rejectsWithoutMutation(400), isFalse);
    expect(
        MutationContract.validatedWrite.rejectsWithoutMutation(409), isFalse);
    expect(MutationContract.panelCreate.rejectsWithoutMutation(400), isTrue);
    expect(MutationContract.entryDelete.rejectsWithoutMutation(409), isTrue);
    expect(MutationContract.plannedDelete.rejectsWithoutMutation(409), isFalse);
    expect(
        MutationContract.cashFlowDelete.rejectsWithoutMutation(422), isFalse);
  });

  for (final owner in [1, 2]) {
    test('logout/login during owner check never sends old intent, owner=$owner',
        () async {
      final (state, api, store) = await fixture(gated: true);
      api.panelResponseLoss = true;
      await state.createPanel(
          panelType: 'claim',
          title: 'fact',
          amount: 500,
          spentOn: '2026-09-17');
      final gate = store as GatedOwnerStore;
      final checked = Completer<void>();
      final release = Completer<void>();
      gate.ownerChecked = checked;
      gate.releaseOwner = release;
      api.panelResponseLoss = false;
      final confirming = state.confirmPendingManualPanelRegistration();
      await checked.future;
      final attempts = api.panelAttempts;
      // Ordinary UI logout/login is blocked by the submit single-flight. Inject
      // an independent session invalidation to exercise the generation fence
      // even if that UI guard is bypassed; this is not normal app interaction.
      state.isBusy = false;
      await state.logout();
      api.ownerId = owner;
      await state.login('owner', 'new-session');
      release.complete();
      expect(await confirming, isFalse);
      expect(api.panelAttempts, attempts);
      expect((await store.loadPendingManualPanelRetry())!.ownerId, 1);
      if (owner == 1) {
        expect(await state.confirmPendingManualPanelRegistration(), isTrue);
        expect(api.panelWrites, 1);
      }
    });
  }

  test(
      'legacy retry binds only to its uniquely matching durable request marker',
      () async {
    final (_, _, store) = await fixture();
    final input = {
      'month': '2026-09',
      'panel_type': 'claim',
      'title': 'old',
      'spent_on': '2026-09-17',
      'amount_value': 500,
      'discount_enabled': true
    };
    final key = await store.reserveManualPanelRetryKey(input);
    final pending = (await store.loadPendingManualPanelRetry())!;
    await expectLater(store.requireManualPanelRetryOwner(pending, 1),
        throwsA(isA<OfflinePersistenceException>()));
    await store.beginOnlineWrite(1, retryIdentity: 'panel:$key');
    await expectLater(store.requireManualPanelRetryOwner(pending, 2),
        throwsA(isA<OfflinePersistenceException>()));
    await store.requireManualPanelRetryOwner(pending, 1);
    expect((await store.loadPendingManualPanelRetry())!.ownerId, 1);
  });

  test('same owner recovers v2 response-loss artifact without duplicate',
      () async {
    final (state, api, store) = await fixture(gated: true);
    api.panelResponseLoss = true;
    await state.createPanel(
        panelType: 'claim',
        title: 'old-format',
        amount: 500,
        spentOn: '2026-09-17');
    final file = File(
        '${(store as GatedOwnerStore).directory.path}/offline-mode/manual-panel-retries.json');
    final content =
        jsonDecode(await file.readAsString()) as Map<String, dynamic>;
    content.remove('owner_id');
    content['schema_version'] = 2;
    await file.writeAsString(jsonEncode(content), flush: true);
    await state.logout();
    await state.login('owner', 'rotated-token');
    api.panelResponseLoss = false;
    expect(await state.confirmPendingManualPanelRegistration(), isTrue);
    expect(api.panelWrites, 1);
    expect(api.panelAttempts, 2);
    expect(await store.loadPendingManualPanelRetry(), isNull);
  });

  for (final status in [404, 409]) {
    test('entry DELETE definite $status clears durable blocker', () async {
      final (state, api, store) = await fixture();
      api.deleteStatus = status;
      await state.deleteExpense(987);
      expect(await store.loadPendingOnlineWrite(1), isNull);
      final restarted = AppState(api, offlineStore: store)
        ..user = baselineFixture().user
        ..isBootstrapping = false;
      addTearDown(restarted.dispose);
      await restarted.refreshInputArea(notify: false);
      expect(await restarted.enterOfflineMode(), isTrue);
    });
  }
  for (final status in [0, 500]) {
    test('entry DELETE ambiguous $status preserves recovery', () async {
      final (state, api, store) = await fixture();
      api.deleteStatus = status;
      await state.deleteExpense(987);
      expect(await store.loadPendingOnlineWrite(1), isNotNull);
      expect(await state.enterOfflineMode(), isFalse);
    });
  }
  test('same owner reauthentication preserves manual retry identity', () async {
    final (state, api, store) = await fixture();
    api.panelResponseLoss = true;
    expect(
        await state.createPanel(
            panelType: 'claim',
            title: 'fact',
            amount: 500,
            spentOn: '2026-09-17'),
        isFalse);
    final key = (await store.loadPendingManualPanelRetry())!.key;
    await state.logout();
    await state.login('owner', 'test');
    api.panelResponseLoss = false;
    expect(await state.confirmPendingManualPanelRegistration(), isTrue);
    expect(api.registered, {key});
    expect(api.panelWrites, 1);
    expect(await store.loadPendingManualPanelRetry(), isNull);
  });
  test('existing second principal cannot resend another owner retry', () async {
    final (state, api, store) = await fixture();
    api.panelResponseLoss = true;
    await state.createPanel(
        panelType: 'claim', title: 'fact', amount: 500, spentOn: '2026-09-17');
    await state.logout();
    api.ownerId = 2;
    await state.login('second', 'test');
    api.panelResponseLoss = false;
    final attempts = api.panelAttempts;
    expect(await state.confirmPendingManualPanelRegistration(), isFalse);
    expect(api.panelAttempts, attempts);
    expect(await store.loadPendingManualPanelRetry(), isNotNull);
  });
}
