// Host-only P1-R-01 baseline and comparison. No platform/device discovery.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/local_snapshot_repository.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/screens/home_shell.dart';

import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/coherent_refresh_models.dart';

import 'support/offline_mode_fixtures.dart';

class NavigationFixture extends OfflineApiFake {
  NavigationFixture(this.n);
  final int n;
  bool changed = false;
  late Uint8List beforeBytes, afterBytes;
  late AuthoritativeStateCandidate initial;
  late LedgerEntry mutationRow;
  int calls = 0;
  Future<void> prepare() async {
    available = true;
    beforeBytes = await super.authoritativeStateBytes();
    changed = true;
    afterBytes = await super.authoritativeStateBytes();
    changed = false;
    initial = AuthoritativeBundle.decode(beforeBytes)
        .toCoherentBundle(baselineFixture().user)
        .candidate;
    mutationRow = AuthoritativeBundle.decode(afterBytes)
        .toCoherentBundle(baselineFixture().user)
        .candidate
        .entries
        .last;
    calls = 0;
  }

  @override
  Future<Uint8List> authoritativeStateBytes() async {
    calls++;
    return changed ? afterBytes : beforeBytes;
  }

  @override
  Future<List<LedgerEntry>> currentEntries() async => List.generate(
      n,
      (i) => LedgerEntry(
          id: i + 1,
          bookSection: 'current',
          entryKind: 'expense',
          title: changed && i == n - 1 ? '갱신된 내역' : '지출 ${i + 1}',
          usagePlace: '가게 ${i + 1}',
          usageItem: '품목',
          sortOrder: i,
          entryDate: '2026-09-17',
          amountValue: 1000,
          paymentKey: 'p102-${i + 1}',
          spendingCategory: changed && i == n - 1 ? 'dignity' : 'essential',
          effectiveAmountValue: 1000));
  @override
  Future<Summary> summary() async => Summary.fromJson({
        ...baselineFixture().toJson()['summary'] as Map<String, dynamic>,
        'current_spending_total': changed ? 23456 : 12345,
        'current_month_spendable': changed ? 65432 : 54321,
      });
  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async => {
        ...await super.offlineReconciliationBaseline(),
        'state_revision': changed ? 2 : 1,
      };
  @override
  Future<LedgerEntry> updateEntryCategory(int id, String? category) async {
    changed = true;
    if (id != mutationRow.id) throw StateError('fixture mutation identity');
    return mutationRow;
  }

  @override
  Future<SnapshotDownload> downloadSnapshot() async => SnapshotDownload(
      filename: 'p102.money-note-snapshot.json',
      bytes: Uint8List.fromList(utf8.encode(jsonEncode(jsonDecode(
          utf8.decode(changed ? afterBytes : beforeBytes))['snapshot']))));
}

class NavigationTransport extends http.BaseClient {
  NavigationTransport(this.bytes);
  final List<int> bytes;
  final requests = <Map<String, Object?>>[];
  int page = 0;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (request.url.host != 'p1r.invalid' ||
        request.method != 'GET' ||
        request.url.path != '/api/authoritative-state') {
      throw StateError('Unexpected synthetic request: ${request.url}');
    }
    requests.add({
      'page_at_dispatch': page,
      'trigger_page': Zone.current[#p1rTrigger],
      'method': request.method,
      'path': request.url.path,
      'bytes': bytes.length
    });
    return http.StreamedResponse(Stream.value(bytes), 200,
        headers: {'content-type': 'application/json'});
  }
}

class NavigationStore extends OfflineStore {
  NavigationStore(Directory directory)
      : super(directoryProvider: () async => directory);
  int replacements = 0;
  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    await super.replaceBaseline(baseline, beforePublish: beforePublish);
    replacements++;
  }
}

class NavigationState extends AppState {
  NavigationState(super.api,
      {required super.offlineStore, required super.snapshotRepository});
  final calls = <int>[];
  final pending = <Future<void>>[];
  final errors = <String>[];
  int notifications = 0;
  Future<void> track(int page, Future<void> Function() operation) {
    calls.add(page);
    // Filesystem futures must use the real event loop in a widget test.
    final observed = Zone.root.run(() => runZoned(
        () => operation().catchError((Object error) {
              // Record expected obsolete requests in their real error zone. Any other
              // exception is a failed experiment, never a successful refresh.
              if (error is! MoneyNoteApiException ||
                  !error.toString().contains('폐기')) {
                throw error;
              }
              errors.add(error.toString());
            }),
        zoneValues: {#p1rTrigger: page}));
    pending.add(observed);
    return observed;
  }

  @override
  Future<void> refresh({bool notify = true}) =>
      track(4, () => super.refresh(notify: notify));
  @override
  Future<void> refreshInputArea({bool notify = true}) =>
      track(0, () => super.refreshInputArea(notify: notify));
  @override
  Future<void> refreshSettlementArea({bool notify = true}) =>
      track(1, () => super.refreshSettlementArea(notify: notify));
  @override
  Future<void> refreshEntriesArea({bool notify = true}) =>
      track(2, () => super.refreshEntriesArea(notify: notify));
  @override
  Future<void> refreshCashArea({bool notify = true}) =>
      track(3, () => super.refreshCashArea(notify: notify));
  @override
  void notifyListeners() {
    notifications++;
    super.notifyListeners();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  if (!Platform.environment.containsKey('P1R_OUTPUT')) {
    navigationRegression();
    return;
  }
  testWidgets('P1-R-01 actual navigation and authoritative HTTP trace',
      (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(400, 800);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        const MethodChannel('money_note/notifications'),
        (call) async => switch (call.method) {
              'permissionStatus' => <String, bool>{
                  'listener_enabled': true,
                  'app_notifications_enabled': true,
                  'battery_unrestricted': true
                },
              'candidateCounts' => <String, int>{'owner': 0, 'family': 0},
              'manualReviewCount' => 0,
              'configureCards' => true,
              _ => null,
            });
    addTearDown(() => tester.binding.defaultBinaryMessenger
        .setMockMethodCallHandler(
            const MethodChannel('money_note/notifications'), null));
    final pilot = Platform.environment['P1R_PILOT'] == '1';
    final controls = Platform.environment['P1R_CONTROLS'] == '1';
    final sizes = controls ? [50] : [50, 1000];
    final root = Directory(Platform.environment['P1_RUN_ROOT']!);
    final samples = <Map<String, Object?>>[];
    final identities = <Map<String, Object?>>[];
    final campaign = Stopwatch()..start();
    for (final n in sizes) {
      final fixture = NavigationFixture(n);
      await tester.runAsync(fixture.prepare);
      identities.add({
        'rows': n,
        'bytes': fixture.beforeBytes.length,
        'sha256': sha256.convert(fixture.beforeBytes).toString()
      });
      final directory =
          await tester.runAsync(() => root.createTemp('navigation-$n-'));
      final transport = NavigationTransport(fixture.beforeBytes);
      final api =
          MoneyNoteApiClient(client: transport, baseUrl: 'https://p1r.invalid');
      final store = NavigationStore(directory!);
      final state = NavigationState(api,
          offlineStore: store,
          snapshotRepository: LocalSnapshotRepository(
              directoryProvider: () async => directory));
      final b = fixture.initial;
      state
        ..isBootstrapping = false
        ..user = b.user
        ..summary = b.summary
        ..cardPaymentStatus = b.cardPaymentStatus
        ..judgment = b.judgment
        ..monthCloseStatus = b.monthCloseStatus
        ..settings = b.settings
        ..ownerDiscountMonth = b.ownerDiscountMonth
        ..familyDiscountMonth = b.familyDiscountMonth
        ..transitDiscountProfile = b.transitDiscountProfile
        ..entries = b.entries
        ..confirmedPlannedEntries = b.confirmedPlannedEntries
        ..panels = b.panels
        ..cashFlows = b.cashFlows;
      final callbacks = <int>[];
      int observedIndex = 0;
      await tester.pumpWidget(NotificationListener<ScrollUpdateNotification>(
          onNotification: (notice) {
            if (notice.depth != 0 || notice.metrics is! PageMetrics) {
              return false;
            }
            // HomeShell's onPageChanged synchronously installs index before
            // this bubbling notification. Observe that actual callback effect;
            // do not infer an HTTP dispatch from it.
            final dynamic shell = tester.state(find.byType(HomeShell));
            final actual = shell.index as int;
            transport.page = actual;
            if (actual != observedIndex) {
              callbacks.add(actual);
              observedIndex = actual;
            }
            return false;
          },
          child: MoneyNoteApp(stateOverride: state, bootstrapOnStart: false)));
      await tester.pumpAndSettle();
      final iterations = pilot ? 1 : 25;
      for (var iteration = 0; iteration < iterations; iteration++) {
        for (final destination in controls ? [1, 0, 0] : [4, 0]) {
          callbacks.clear();
          state.calls.clear();
          state.errors.clear();
          state.pending.clear();
          transport.requests.clear();
          final oldReplacements = store.replacements;
          final oldNotifications = state.notifications;
          final origin = observedIndex;
          final watch = Stopwatch()..start();
          final menu = tester.widget<NavigationBar>(find.byType(NavigationBar));
          menu.onDestinationSelected!(destination);
          for (var frame = 0; frame < 16; frame++) {
            await tester.pump(const Duration(milliseconds: 16));
            await tester.runAsync(() => Future<void>.delayed(Duration.zero));
          }
          await tester.runAsync(() => Future.wait(state.pending));
          await tester.pumpAndSettle();
          watch.stop();
          final dynamic shell = tester.state(find.byType(HomeShell));
          expect(shell.index, destination);
          expect(
              tester
                  .widget<NavigationBar>(find.byType(NavigationBar))
                  .selectedIndex,
              destination);
          if (pilot || iteration >= 5) {
            samples.add({
              'rows': n,
              'sample': pilot ? iteration : iteration - 5,
              'origin': origin,
              'destination': destination,
              'elapsed_us': watch.elapsedMicroseconds,
              'callbacks': List<int>.from(callbacks),
              'refresh_entries': List<int>.from(state.calls),
              'http': List<Map<String, Object?>>.from(transport.requests),
              'durable_replacements': store.replacements - oldReplacements,
              'notifications': state.notifications - oldNotifications,
              'errors': List<String>.from(state.errors)
            });
          }
          if (campaign.elapsed.inSeconds > 600) {
            throw StateError('P1-R-01 measurement budget exceeded');
          }
        }
      }
      await tester.pumpWidget(const SizedBox.shrink());
      state.dispose();
      transport.close();
      await tester.runAsync(() => directory.delete(recursive: true));
    }
    await tester.runAsync(() =>
        File(Platform.environment['P1R_OUTPUT']!).writeAsString(jsonEncode({
          'fixtures': identities,
          'samples': samples,
          'elapsed_s': campaign.elapsedMilliseconds / 1000,
          'callback_observation': 'onPageChanged synchronous index changes',
          'get_observation': 'BaseClient.send, synthetic host only'
        })));
  }, timeout: const Timeout(Duration(minutes: 11)));
}

void navigationRegression() {
  testWidgets('P1-R-01 navigation freshness, interaction and form lifecycle',
      (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(400, 800);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        const MethodChannel('money_note/notifications'),
        (call) async => switch (call.method) {
              'permissionStatus' => <String, bool>{
                  'listener_enabled': true,
                  'app_notifications_enabled': true,
                  'battery_unrestricted': true
                },
              'candidateCounts' => <String, int>{'owner': 0, 'family': 0},
              'manualReviewCount' => 0,
              'configureCards' => true,
              _ => null,
            });
    addTearDown(() => tester.binding.defaultBinaryMessenger
        .setMockMethodCallHandler(
            const MethodChannel('money_note/notifications'), null));
    final fixture = NavigationFixture(50);
    await tester.runAsync(fixture.prepare);
    final directory = (await tester
        .runAsync(() => Directory.systemTemp.createTemp('p1r-functional-')))!;
    final transport = NavigationTransport(fixture.beforeBytes);
    final store = NavigationStore(directory);
    final state = NavigationState(
        MoneyNoteApiClient(client: transport, baseUrl: 'https://p1r.invalid'),
        offlineStore: store,
        snapshotRepository:
            LocalSnapshotRepository(directoryProvider: () async => directory));
    final b = fixture.initial;
    state
      ..isBootstrapping = false
      ..user = b.user
      ..summary = b.summary
      ..cardPaymentStatus = b.cardPaymentStatus
      ..judgment = b.judgment
      ..monthCloseStatus = b.monthCloseStatus
      ..settings = b.settings
      ..ownerDiscountMonth = b.ownerDiscountMonth
      ..familyDiscountMonth = b.familyDiscountMonth
      ..transitDiscountProfile = b.transitDiscountProfile
      ..entries = b.entries
      ..confirmedPlannedEntries = b.confirmedPlannedEntries
      ..panels = b.panels
      ..cashFlows = b.cashFlows;
    final expectJump = Platform.environment['P1R_EXPECT_JUMP'] == '1';
    final checks = <String>[];
    var disposed = false;
    void select(int index) => tester
        .widget<NavigationBar>(find.byType(NavigationBar))
        .onDestinationSelected!(index);
    void clear() {
      state.pending.clear();
      state.calls.clear();
      state.errors.clear();
      transport.requests.clear();
    }

    Future<void> settle(int index) async {
      for (var i = 0; i < 18; i++) {
        await tester.pump(const Duration(milliseconds: 16));
        await tester.runAsync(() => Future<void>.delayed(Duration.zero));
      }
      await tester.runAsync(() => Future.wait(state.pending));
      await tester.pumpAndSettle();
      expect(
          tester
              .widget<NavigationBar>(find.byType(NavigationBar))
              .selectedIndex,
          index);
      final dynamic shell = tester.state(find.byType(HomeShell));
      expect(shell.index, index);
    }

    try {
      await tester.pumpWidget(
          MoneyNoteApp(stateOverride: state, bootstrapOnStart: false));
      await tester.pumpAndSettle();
      expect(
          MediaQuery.textScalerOf(tester.element(find.byType(HomeShell)))
              .scale(1),
          1);
      clear();
      select(4);
      await settle(4);
      expect(transport.requests.where((r) => r['trigger_page'] == 4).length, 1);
      if (expectJump) expect(transport.requests.length, 1);
      checks.add('distant destination refresh');
      clear();
      select(4);
      await settle(4);
      expect(transport.requests, isEmpty);
      checks.add('same-tab no-op');
      clear();
      select(3);
      await settle(3);
      expect(state.calls, [3]);
      expect(transport.requests.length, 1);
      checks.add('adjacent animation and refresh');
      clear();
      await tester.drag(find.byType(PageView), const Offset(300, 0));
      await settle(2);
      expect(state.calls, [2]);
      checks.add('manual swipe and refresh');
      clear();
      select(0);
      await settle(0);
      expect(transport.requests.where((r) => r['trigger_page'] == 0).length, 1);
      if (expectJump) expect(transport.requests.length, 1);
      checks.add('reverse distant destination refresh');
      clear();
      select(4);
      for (var i = 0; i < 3; i++) {
        await tester.pump(const Duration(milliseconds: 16));
        await tester.runAsync(() => Future<void>.delayed(Duration.zero));
      }
      select(0);
      await settle(0);
      checks.add('rapid reversal');
      clear();
      select(1);
      await tester.pump(const Duration(milliseconds: 32));
      select(4);
      await settle(4);
      checks.add('selection during adjacent animation');
      clear();
      select(2);
      await settle(2);
      final input = find.byType(TextField).first;
      await tester.enterText(input, 'P1-R 입력 보존');
      final focus = FocusManager.instance.primaryFocus;
      state.notifyListeners();
      await tester.pump();
      expect(find.text('P1-R 입력 보존'), findsOneWidget);
      expect(FocusManager.instance.primaryFocus, same(focus));
      checks.add('draft/focus on parent notification');
      clear();
      await tester.runAsync(state.refreshEntriesArea);
      await tester.pumpAndSettle();
      expect(find.text('P1-R 입력 보존'), findsOneWidget);
      expect(FocusManager.instance.primaryFocus, same(focus));
      checks.add('draft/focus on authoritative refresh');
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      clear();
      select(1);
      await tester.pump(const Duration(milliseconds: 16));
      await tester.pumpWidget(const SizedBox.shrink());
      state.dispose();
      disposed = true;
      await tester.runAsync(() => Future.wait(state.pending));
      await tester.pumpAndSettle();
      checks.add('dispose during navigation');
      final output = Platform.environment['P1R_FUNCTIONAL_OUTPUT'];
      if (output != null) {
        await tester.runAsync(
            () => File(output).writeAsString(jsonEncode({'checks': checks})));
      }
    } finally {
      await tester.pumpWidget(const SizedBox.shrink());
      if (!disposed) state.dispose();
      await tester.runAsync(() => Future.wait(state.pending));
      transport.close();
      await tester.runAsync(() => directory.delete(recursive: true));
    }
  });
}
