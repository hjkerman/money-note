import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/coherent_refresh_coordinator.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/offline/online_write_state.dart';

import 'support/offline_mode_fixtures.dart';

class DagApi extends OfflineApiFake {
  final calls = <String>[];
  final counts = <String, int>{};
  final gates = <String, Completer<void>>{};
  final failures = <String, Object>{};
  final started = <String, Completer<void>>{};
  final policyMonths = <String>[];
  String? cashFrom;
  String? cashTo;
  String date = '2026-09-17';
  String month = '2026-09';
  bool mismatchRevision = false;
  bool crossMidnight = false;
  int writes = 0;
  List<LedgerEntry>? entryRows;
  List<MonthlyPanel>? panelRows;

  Future<T> read<T>(String name, Future<T> Function() build) async {
    final ordinal = (counts[name] ?? 0) + 1;
    counts[name] = ordinal;
    final key = '$name#$ordinal';
    calls.add(key);
    started.putIfAbsent(key, Completer<void>.new).complete();
    final gate = gates[key];
    if (gate != null) await gate.future;
    final error = failures[name];
    if (error != null) throw error;
    return build();
  }

  Future<void> requested(String key) =>
      started.putIfAbsent(key, Completer<void>.new).future;

  void hold(String key) => gates[key] = Completer<void>();
  void releaseAll() {
    for (final gate in gates.values) {
      if (!gate.isCompleted) gate.complete();
    }
  }

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() =>
      read('baseline', () async {
        final value = await super.offlineReconciliationBaseline();
        final n = counts['baseline']!;
        return {
          ...value,
          'state_revision': mismatchRevision ? n : value['state_revision'],
          'evaluation_date': crossMidnight && n > 1 ? '2026-10-01' : date,
        };
      });

  @override
  Future<MonthCloseStatus> monthCloseStatus() => read('status', () async {
        final crossed = crossMidnight && counts['baseline']! > 1;
        return MonthCloseStatus.fromJson({
          'calendar_date': crossed ? '2026-10-01' : date,
          'calendar_month': crossed ? '2026-10' : month,
        });
      });

  @override
  Future<Summary> summary() {
    final captured =
        baselineFixture(remainingLiquidity: remainingLiquidity).summary;
    return read('summary', () async => captured);
  }

  @override
  Future<CardPaymentStatus> currentCardPaymentStatus() =>
      read('payment', super.currentCardPaymentStatus);
  @override
  Future<JudgmentState> judgment() => read('judgment', super.judgment);
  @override
  Future<List<LedgerEntry>> currentEntries() =>
      read('entries', () async => entryRows ?? baselineFixture().entries);
  @override
  Future<List<LedgerEntry>> confirmedPlannedEntries() =>
      read('confirmed', super.confirmedPlannedEntries);
  @override
  Future<List<MonthlyPanel>> currentPanels() =>
      read('panels', () async => panelRows ?? baselineFixture().panels);
  @override
  Future<AppSettings> settings() => read('settings', super.settings);
  @override
  Future<List<CashFlow>> cashFlows(
      {String? dateFrom, String? dateTo, int? limit}) {
    cashFrom = dateFrom;
    cashTo = dateTo;
    return read('cash', () async => const []);
  }

  @override
  Future<CardDiscountMonth> discountMonth(String month, String scope) {
    policyMonths.add('$scope:$month');
    return read(
        scope,
        () async =>
            CardDiscountMonth(month: month, scope: scope, policy: 'enabled'));
  }

  @override
  Future<TransitDiscountProfileStatus> transitDiscountProfile(String month) {
    policyMonths.add('transit:$month');
    return read(
        'transit',
        () async =>
            TransitDiscountProfileStatus(month: month, profile: 'owner'));
  }

  @override
  Future<void> logout() async {}

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
    committed = true;
    remainingLiquidity -= amount;
    return LedgerEntry(
        id: writes,
        bookSection: 'current',
        entryKind: 'expense',
        title: usageItem,
        sortOrder: 1,
        amountValue: amount,
        entryDate: date);
  }
}

class CountingBaselineStore extends OfflineStore {
  CountingBaselineStore(Directory directory)
      : super(directoryProvider: () async => directory);
  int publications = 0;

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    await super.replaceBaseline(baseline, beforePublish: beforePublish);
    publications++;
  }
}

class MalformedSettingsApi extends DagApi {
  final decoder = MoneyNoteApiClient(
      baseUrl: 'https://example.invalid',
      client: MockClient((_) async => http.Response('[]', 200)));

  @override
  Future<AppSettings> settings() => decoder.settings();
}

Future<void> drain() async {
  for (var i = 0; i < 12; i++) {
    await Future<void>.delayed(Duration.zero);
  }
}

CoherentRefreshCoordinator coordinator(DagApi api) =>
    CoherentRefreshCoordinator(api,
        localToday: () => '2035-01-07',
        formatDate: (date) =>
            '${date.year}-${date.month.toString().padLeft(2, '0')}-'
            '${date.day.toString().padLeft(2, '0')}');

Future<(AppState, CountingBaselineStore)> seededState(DagApi api) async {
  final directory = await Directory.systemTemp.createTemp('money-note-dag-');
  addTearDown(() => directory.delete(recursive: true));
  final store = CountingBaselineStore(directory);
  await store.replaceBaseline(baselineFixture());
  store.publications = 0;
  final state = AppState(api, offlineStore: store)
    ..user = baselineFixture().user
    ..summary = baselineFixture().summary
    ..isBootstrapping = false;
  addTearDown(state.dispose);
  return (state, store);
}

Future<bool> submit(AppState state) => state.createExpense(
    usagePlace: 'shop',
    usageItem: 'fact',
    amount: 500,
    discountEnabled: true,
    entryDate: '2026-09-17');

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
      'independent reads overlap status, but cash keeps its server-date dependency',
      () async {
    final api = DagApi()..hold('status#1');
    final acquiring = coordinator(api)
        .acquireLegacyForDiagnostics(() => baselineFixture().user);
    await api.requested('status#1');
    await drain();
    final independent = [
      'summary',
      'payment',
      'judgment',
      'entries',
      'confirmed',
      'panels',
      'settings'
    ].every((name) => api.counts[name] == 1);
    final cash = api.counts['cash'] ?? 0;
    final policies = api.policyMonths.length;
    api.releaseAll();
    final bundle = await acquiring;
    expect(independent, isTrue);
    expect(cash, 0);
    expect(policies, 0);
    expect(api.cashFrom, '2026-08-01');
    expect(api.cashTo, '2026-09-30');
    expect(bundle.candidate.monthCloseStatus.calendarDate, '2026-09-17');
    expect(api.calls.length, 14);
  });

  test('policies overlap slow cash without waiting for its unrelated result',
      () async {
    final api = DagApi()..hold('cash#1');
    final acquiring = coordinator(api)
        .acquireLegacyForDiagnostics(() => baselineFixture().user);
    await api.requested('cash#1');
    await drain();
    final policies = api.policyMonths.length;
    final envelopes = api.counts['baseline'];
    api.releaseAll();
    await acquiring;
    expect(policies, 3);
    expect(envelopes, 1); // the closing fence cannot race unfinished reads.
    expect(api.counts['baseline'], 2);
  });

  test('policy phase waits for core reads to bound SQLite competition',
      () async {
    final api = DagApi()..hold('summary#1');
    final acquiring = coordinator(api)
        .acquireLegacyForDiagnostics(() => baselineFixture().user);
    await api.requested('summary#1');
    await drain();
    final startedPolicies = api.policyMonths.length;
    api.releaseAll();
    await acquiring;
    expect(startedPolicies, 0);
    expect(api.policyMonths.length, 3);
  });

  test('both envelope fences stay outside the entire candidate graph',
      () async {
    final api = DagApi()
      ..hold('baseline#1')
      ..hold('transit#1');
    final acquiring = coordinator(api)
        .acquireLegacyForDiagnostics(() => baselineFixture().user);
    await api.requested('baseline#1');
    await drain();
    expect(api.calls, ['baseline#1']);
    api.gates['baseline#1']!.complete();
    await api.requested('transit#1');
    await drain();
    expect(api.counts['baseline'], 1);
    api.releaseAll();
    await acquiring;
    expect(api.calls.last, 'baseline#2');
  });

  for (final input in ['entries', 'panels']) {
    test('policy month waits for $input fallback evidence', () async {
      final api = DagApi()
        ..month = ''
        ..hold('$input#1');
      final acquiring = coordinator(api)
          .acquireLegacyForDiagnostics(() => baselineFixture().user);
      await api.requested('$input#1');
      await drain();
      expect(api.policyMonths, isEmpty);
      api.releaseAll();
      await acquiring;
      expect(api.policyMonths,
          ['owner:2026-09', 'family:2026-09', 'transit:2026-09']);
    });
  }

  test('server month beats occurrence month and device date', () async {
    final api = DagApi()
      ..entryRows = [
        LedgerEntry(
            id: 1,
            bookSection: 'current',
            entryKind: 'expense',
            title: 'old date',
            sortOrder: 1,
            entryDate: '2024-01-01')
      ];
    await coordinator(api)
        .acquireLegacyForDiagnostics(() => baselineFixture().user);
    expect(
        api.policyMonths.every((value) => value.endsWith('2026-09')), isTrue);
  });

  test('server leap-day controls cash query bounds', () async {
    final api = DagApi()
      ..date = '2024-02-29'
      ..month = '2024-02';
    await coordinator(api)
        .acquireLegacyForDiagnostics(() => baselineFixture().user);
    expect(api.cashFrom, '2024-01-01');
    expect(api.cashTo, '2024-02-29');
  });

  test('missing server month retains occurrence-date fallback', () async {
    final api = DagApi()
      ..month = ''
      ..entryRows = [
        LedgerEntry(
            id: 1,
            bookSection: 'current',
            entryKind: 'expense',
            title: 'edited',
            sortOrder: 1,
            entryDate: '2026-08-21')
      ];
    await coordinator(api)
        .acquireLegacyForDiagnostics(() => baselineFixture().user);
    expect(
        api.policyMonths.every((value) => value.endsWith('2026-08')), isTrue);
  });

  test('missing month/occurrence retains panel then local fallback', () async {
    for (final emptyPanels in [false, true]) {
      final api = DagApi()
        ..month = ''
        ..entryRows = [];
      if (emptyPanels) api.panelRows = [];
      await coordinator(api)
          .acquireLegacyForDiagnostics(() => baselineFixture().user);
      final expected = emptyPanels ? '2035-01' : '2026-09';
      expect(
          api.policyMonths.every((value) => value.endsWith(expected)), isTrue);
    }
  });

  test('fast branch failure still drains a slow sibling without publication',
      () async {
    final api = DagApi()
      ..failures['owner'] = MoneyNoteApiException('rejected', statusCode: 422)
      ..hold('cash#1');
    final (state, store) = await seededState(api);
    final submitting = submit(state);
    await api.requested('owner#1');
    await drain();
    expect(state.isBusy, isTrue);
    expect(api.counts['baseline'], 1);
    expect(store.publications, 0);
    api.releaseAll();
    expect(await submitting, isFalse);
    expect(state.onlineWriteStatus,
        OnlineWriteStatus.serverCommittedRebuildPending);
  });

  test('closing fence remains before durable publication and submit unlock',
      () async {
    final api = DagApi()..hold('baseline#2');
    final (state, store) = await seededState(api);
    final submitting = submit(state);
    await api.requested('baseline#2');
    await drain();
    expect(state.isBusy, isTrue);
    expect(state.summary!.remainingLiquidity, 10000);
    expect(store.publications, 0);
    expect((await store.loadPendingOnlineWrite(1))!.status,
        OnlineWriteStatus.serverCommittedRebuildPending);
    api.releaseAll();
    expect(await submitting, isTrue);
    expect(state.isBusy, isFalse);
    expect(state.authoritativeRebuildPending, isFalse);
    expect(store.publications, 1);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 9500);
    expect(await store.loadPendingOnlineWrite(1), isNull);
    expect(api.calls.length, 14);
  });

  test('real API malformed JSON shape rejects the whole candidate', () async {
    final api = MalformedSettingsApi();
    final (state, store) = await seededState(api);
    expect(await submit(state), isFalse);
    expect(store.publications, 0);
    expect(state.summary!.remainingLiquidity, 10000);
    expect(state.onlineWriteStatus,
        OnlineWriteStatus.serverCommittedRebuildPending);
  });

  test('midnight/month change rejects first candidate and retries full graph',
      () async {
    final api = DagApi()
      ..date = '2026-09-30'
      ..month = '2026-09'
      ..crossMidnight = true;
    final bundle = await coordinator(api)
        .acquireLegacyForDiagnostics(() => baselineFixture().user);
    expect(api.counts['baseline'], 4);
    expect(api.calls.length, 28);
    expect(bundle.candidate.monthCloseStatus.calendarDate, '2026-10-01');
    expect(bundle.candidate.ownerDiscountMonth.month, '2026-10');
    expect(api.cashFrom, '2026-09-01');
    expect(api.cashTo, '2026-10-31');
  });

  test(
      'equal fingerprint cannot hide revision changes or retire committed pending',
      () async {
    final api = DagApi()..mismatchRevision = true;
    final (state, store) = await seededState(api);
    expect(await submit(state), isFalse);
    expect(api.counts['baseline'], 6);
    expect(store.publications, 0);
    expect(state.onlineWriteStatus,
        OnlineWriteStatus.serverCommittedRebuildPending);
    expect(await state.enterOfflineMode(), isFalse);
  });

  final failures = <String, Object Function()>{
    'fast rejection': () =>
        MoneyNoteApiException('read rejected', statusCode: 422),
    'slow failure': () => StateError('read failed'),
    'timeout': () => MoneyNoteConnectionException('read timed out'),
    'malformed decode': () => const FormatException('malformed response'),
    'auth rejection': () => MoneyNoteApiException('revoked', statusCode: 401),
    'cancelled request': () => MoneyNoteConnectionException('read cancelled'),
  };
  for (final endpoint in [
    'status',
    'summary',
    'payment',
    'judgment',
    'entries',
    'confirmed',
    'panels',
    'settings',
    'cash',
    'owner',
    'family',
    'transit'
  ]) {
    for (final failure in failures.entries) {
      test(
          '$endpoint ${failure.key} preserves baseline and committed retry marker',
          () async {
        final api = DagApi()..failures[endpoint] = failure.value();
        if (failure.key == 'slow failure') api.hold('$endpoint#1');
        final (state, store) = await seededState(api);
        final previous = jsonEncode((await store.loadBaseline())!.toJson());
        final submitting = submit(state);
        await api.requested('$endpoint#1');
        await drain();
        expect(store.publications, 0);
        expect(state.summary!.remainingLiquidity, 10000);
        if (failure.key == 'slow failure') expect(state.isBusy, isTrue);
        api.releaseAll();
        expect(await submitting, isFalse);
        expect(store.publications, 0);
        expect(jsonEncode((await store.loadBaseline())!.toJson()), previous);
        expect(state.onlineWriteStatus,
            OnlineWriteStatus.serverCommittedRebuildPending);
        expect((await store.loadPendingOnlineWrite(1))!.status,
            OnlineWriteStatus.serverCommittedRebuildPending);
        expect(await state.enterOfflineMode(), isFalse);
        api.failures.clear();
        expect(await state.rebuildAfterOnlineWrite(), isTrue);
        expect(api.writes,
            1); // read-only recovery, never repeat the financial POST.
        expect(state.authoritativeRebuildPending, isFalse);
        expect(store.publications, 1);
      });
    }
  }

  test('late graph A cannot overwrite newer refresh B', () async {
    final api = DagApi()..hold('summary#1');
    final (state, store) = await seededState(api);
    final old = state.refreshInputArea(notify: false);
    final rejected = expectLater(old, throwsA(isA<MoneyNoteApiException>()));
    await api.requested('summary#1');
    api.remainingLiquidity = 22222;
    await state.refreshInputArea(notify: false);
    api.releaseAll();
    await rejected;
    expect(state.summary!.remainingLiquidity, 22222);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 22222);
    expect(store.publications, 1);
  });

  test('late policy branch A cannot overwrite newer graph B', () async {
    final api = DagApi()..hold('transit#1');
    final (state, store) = await seededState(api);
    final old = state.refreshInputArea(notify: false);
    final rejected = expectLater(old, throwsA(isA<MoneyNoteApiException>()));
    await api.requested('transit#1');
    api.remainingLiquidity = 33333;
    await state.refreshInputArea(notify: false);
    api.releaseAll();
    await rejected;
    expect(state.summary!.remainingLiquidity, 33333);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 33333);
    expect(store.publications, 1);
  });

  test(
      'new mutation revokes a late graph even if acquisition retries coherently',
      () async {
    final api = DagApi()..hold('summary#1');
    final (state, store) = await seededState(api);
    final old = state.refreshInputArea(notify: false);
    final rejected = expectLater(old, throwsA(isA<MoneyNoteApiException>()));
    await api.requested('summary#1');
    expect(await submit(state), isTrue);
    api.releaseAll();
    await rejected;
    expect(state.summary!.remainingLiquidity, 9500);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 9500);
    expect(api.writes, 1);
    expect(store.publications, 1);
  });

  test('logout and same-owner reauthentication revoke late graph installation',
      () async {
    final api = DagApi()..hold('summary#1');
    final (state, store) = await seededState(api);
    final old = state.refreshInputArea(notify: false);
    final rejected = expectLater(old, throwsA(isA<MoneyNoteApiException>()));
    await api.requested('summary#1');
    await state.logout();
    state.user = baselineFixture().user;
    api.remainingLiquidity = 7777;
    await state.refreshInputArea(notify: false);
    api.releaseAll();
    await rejected;
    expect(state.summary!.remainingLiquidity, 7777);
    expect((await store.loadBaseline())!.summary.remainingLiquidity, 7777);
    expect(store.publications, 1);
  });
}
