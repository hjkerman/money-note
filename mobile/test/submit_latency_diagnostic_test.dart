import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'support/offline_mode_fixtures.dart';

class _MutationApi extends OfflineApiFake {
  int expenseCalls = 0;
  int cashCalls = 0;
  int panelCalls = 0;
  int baselineCalls = 0;

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async {
    baselineCalls += 1;
    return super.offlineReconciliationBaseline();
  }

  @override
  Future<LedgerEntry> createExpense({
    required String date,
    required String usagePlace,
    required String usageItem,
    required int amount,
    required bool discountEnabled,
    int? discountOverrideAmount,
    String? spendingCategory,
    String? candidateRegistrationKey,
  }) async {
    expenseCalls += 1;
    remainingLiquidity -= amount;
    return LedgerEntry(
      id: expenseCalls,
      bookSection: 'current',
      entryKind: 'expense',
      title: usageItem,
      sortOrder: expenseCalls,
      entryDate: date,
      usagePlace: usagePlace,
      usageItem: usageItem,
      amountValue: amount,
    );
  }

  @override
  Future<CashFlow> createCashFlow({
    required String occurredOn,
    required String title,
    required int amount,
    required bool isPrimaryIncome,
  }) async {
    cashCalls += 1;
    remainingLiquidity += amount;
    return CashFlow(
      id: cashCalls,
      occurredOn: occurredOn,
      title: title,
      amountValue: amount,
      sortOrder: cashCalls,
      isPrimaryIncome: isPrimaryIncome,
    );
  }

  @override
  Future<MonthlyPanel> createPanel({
    required String month,
    required String panelType,
    required String title,
    required int amount,
    String? spentOn,
    String? candidateRegistrationKey,
    bool? initialDiscountEnabled,
  }) async {
    panelCalls += 1;
    return MonthlyPanel(
      id: panelCalls,
      month: month,
      panelType: panelType,
      title: title,
      sortOrder: panelCalls,
      amountValue: amount,
      spentOn: spentOn,
      discountAmount: 0,
      discountOverride: initialDiscountEnabled == false ? 1 : 0,
    );
  }
}

class _PausingBaselineStore extends OfflineStore {
  _PausingBaselineStore(Directory directory)
      : super(directoryProvider: () async => directory);

  final started = Completer<void>();
  final release = Completer<void>();

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    started.complete();
    await release.future;
    await super.replaceBaseline(baseline, beforePublish: beforePublish);
  }
}

class _CountingBaselineStore extends OfflineStore {
  _CountingBaselineStore(Directory directory)
      : super(directoryProvider: () async => directory);

  int replacements = 0;

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    replacements += 1;
    await super.replaceBaseline(baseline, beforePublish: beforePublish);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('financial submits persist coherent state without scanning native inbox',
      () async {
    const channel = MethodChannel('money_note/notifications');
    final calls = <String>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
      calls.add(call.method);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      return switch (call.method) {
        'permissionStatus' => <String, bool>{
            'listener_enabled': true,
            'app_notifications_enabled': true,
            'battery_unrestricted': true,
          },
        'candidateCounts' => <String, int>{'owner': 0, 'family': 0},
        'manualReviewCount' => 0,
        'configureCards' => true,
        _ => null,
      };
    });
    addTearDown(() => TestDefaultBinaryMessengerBinding
        .instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null));
    final directory = await temporaryDirectoryFixture();
    final store = _CountingBaselineStore(directory);
    final api = _MutationApi()..available = true;
    final state = AppState(api, offlineStore: store)
      ..user = baselineFixture().user;

    final cardWatch = Stopwatch()..start();
    expect(
        await state.createExpense(
          usagePlace: '가게',
          usageItem: '식사',
          amount: 1000,
          discountEnabled: true,
        ),
        isTrue);
    cardWatch.stop();
    expect(api.expenseCalls, 1);
    expect(api.bundleCalls, 1);
    // Legacy calls below construct the synthetic server byte response inside
    // this model double; they are not normal application HTTP requests.
    expect(api.baselineCalls, 2);
    expect(api.stateFetchCalls, 12);
    expect(store.replacements, 1);
    expect(state.summary!.remainingLiquidity, 9000);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 9000);
    expect(calls, isEmpty);

    final cashWatch = Stopwatch()..start();
    expect(
        await state.createCashFlow(
          occurredOn: '2026-09-17',
          title: '입금',
          amount: 500,
          isIncome: true,
          isPrimaryIncome: false,
        ),
        isTrue);
    cashWatch.stop();
    expect(api.cashCalls, 1);
    expect(api.bundleCalls, 2);
    expect(api.baselineCalls, 4);
    expect(api.stateFetchCalls, 24);
    expect(store.replacements, 2);
    expect(state.summary!.remainingLiquidity, 9500);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 9500);
    expect(calls, isEmpty);

    for (final panelType in ['claim', 'family_card']) {
      expect(
          await state.createPanel(
            panelType: panelType,
            title: '정산',
            amount: 1000,
          ),
          isTrue);
      expect(calls, isEmpty);
    }
    expect(api.panelCalls, 2);
    expect(api.bundleCalls, 4);
    expect(api.baselineCalls, 8);
    expect(api.stateFetchCalls, 48);
    expect(store.replacements, 4);
    expect(await store.hasPendingManualPanelRetry(), isFalse);

    final fullWatch = Stopwatch()..start();
    await state.refresh();
    fullWatch.stop();
    debugPrint(
        'controlled native 4x50 ms: card=${cardWatch.elapsedMilliseconds} ms, cash=${cashWatch.elapsedMilliseconds} ms, fullRefresh=${fullWatch.elapsedMilliseconds} ms');
    expect(api.baselineCalls, 10);
    expect(api.stateFetchCalls, 60);
    expect(
        calls,
        containsAll(<String>[
          'permissionStatus',
          'configureCards',
          'candidateCounts',
          'manualReviewCount',
        ]));
    calls.clear();
    await state.refreshSettingsArea(notify: false);
    expect(calls, contains('configureCards'));
    calls.clear();
    await state.refreshInputArea();
    expect(calls, contains('candidateCounts'));
  });

  test('durable baseline still gates success and duplicate financial submits',
      () async {
    final directory = await temporaryDirectoryFixture();
    final store = _PausingBaselineStore(directory);
    final api = _MutationApi()..available = true;
    final state = AppState(api, offlineStore: store)
      ..user = baselineFixture().user;

    final pending = state.createExpense(
      usagePlace: '가게',
      usageItem: '식사',
      amount: 1000,
      discountEnabled: true,
    );
    await store.started.future;
    expect(state.isBusy, isTrue);
    expect(state.summary, isNull);
    expect(await store.loadBaseline(), isNull);
    expect(
        await state.createCashFlow(
          occurredOn: '2026-09-17',
          title: '중복 입력',
          amount: 500,
          isIncome: true,
          isPrimaryIncome: false,
        ),
        isFalse);
    expect(api.cashCalls, 0);

    store.release.complete();
    expect(await pending, isTrue);
    expect(state.isBusy, isFalse);
    expect(state.summary!.remainingLiquidity, 9000);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 9000);
  });

  test('diagnose baseline serialization and event-loop delay', () async {
    final base = baselineFixture();
    final rows = List.generate(
        4000,
        (index) => {
              'id': index + 1,
              'entry_date': '2026-09-17',
              'title': '합성 지출 $index',
              'usage_place': '합성 가게',
              'usage_item': '합성 항목',
              'amount_value': 1000,
              'discount_override': 0,
              'aux_amount_value': null,
              'sort_order': index,
            });
    final snapshot = {
      'schema_version': 2,
      'exported_at': '2026-09-17T03:14:00Z',
      'data': {'ledger_entries': rows},
    };
    final baseline = OfflineBaseline(
      syncedAt: base.syncedAt,
      user: base.user,
      summary: base.summary,
      cardPaymentStatus: base.cardPaymentStatus,
      judgment: base.judgment,
      monthCloseStatus: base.monthCloseStatus,
      settings: base.settings,
      ownerDiscountMonth: base.ownerDiscountMonth,
      familyDiscountMonth: base.familyDiscountMonth,
      transitDiscountProfile: base.transitDiscountProfile,
      entries: base.entries,
      confirmedPlannedEntries: base.confirmedPlannedEntries,
      panels: base.panels,
      cashFlows: base.cashFlows,
      authoritativeSnapshot: snapshot,
      serverStateFingerprint: base.serverStateFingerprint,
      discountPolicyDefaults: base.discountPolicyDefaults,
    );
    final directory = await Directory.systemTemp.createTemp('submit-latency-');
    addTearDown(() => directory.delete(recursive: true));
    final store = OfflineStore(directoryProvider: () async => directory);

    final serialize = Stopwatch()..start();
    final payload = baseline.toJson();
    final toJsonMs = serialize.elapsedMilliseconds;
    final encoded = jsonEncode(payload);
    final encodeMs = serialize.elapsedMilliseconds - toJsonMs;
    jsonDecode(encoded);
    final decodeMs = serialize.elapsedMilliseconds - toJsonMs - encodeMs;

    var maxEventLoopGap = Duration.zero;
    var lastTick = DateTime.now();
    final timer = Timer.periodic(const Duration(milliseconds: 1), (_) {
      final now = DateTime.now();
      final gap = now.difference(lastTick);
      if (gap > maxEventLoopGap) maxEventLoopGap = gap;
      lastTick = now;
    });
    await Future<void>.delayed(const Duration(milliseconds: 5));
    final persistence = Stopwatch()..start();
    await store.replaceBaseline(baseline);
    final persistenceMs = persistence.elapsedMilliseconds;
    await Future<void>.delayed(const Duration(milliseconds: 5));
    timer.cancel();
    debugPrint(
        'synthetic 4000 rows ${encoded.length} bytes: toJson=$toJsonMs ms, encode=$encodeMs ms, decode=$decodeMs ms, fullPersistence=$persistenceMs ms, maxEventLoopGap=${maxEventLoopGap.inMilliseconds} ms');
    expect((await store.loadBaseline())!.serverStateFingerprint,
        base.serverStateFingerprint);
  });
}
