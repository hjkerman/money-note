// P1-01 only. Run normally for functional tests; P101_MODE=benchmark for
// wall-clock host samples. No HTTP, persistence, device or virtual frame timing.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/screens/input_screen.dart';
import 'package:money_note_mobile/src/screens/month_entries_screen.dart';
import 'package:money_note_mobile/src/theme.dart';

import 'support/offline_mode_fixtures.dart';

List<LedgerEntry> fixture(int count) => List.generate(
    count,
    (i) => LedgerEntry(
          id: i + 1,
          bookSection: 'current',
          entryKind: 'expense',
          title: '지출 ${i + 1}',
          sortOrder: i,
          entryDate: '2026-10-03',
          usagePlace: '가게 ${i + 1}',
          usageItem: '품목 ${i + 1}',
          amountValue: 10000,
          paymentKey: 'p101-${i + 1}',
          spendingCategory: 'essential',
          discountPolicy: 'enabled',
          automaticDiscountEligible: true,
          automaticDiscountAmount: 120,
          effectiveDiscountAmount: 120,
          effectiveAmountValue: 9880,
        ));

class P101State extends AppState {
  P101State(List<LedgerEntry> rows) : super(OfflineApiFake()) {
    final base = baselineFixture();
    entries = rows;
    summary = base.summary;
    monthCloseStatus = base.monthCloseStatus;
  }
  final actions = <String>[];
  Completer<bool>? completion;
  int submitCalls = 0;
  int refreshCalls = 0;
  void changed() => notifyListeners();
  @override
  Future<void> updateExpenseCategory(int id, String? category) async {
    actions.add('category:$id:$category');
  }

  @override
  Future<void> excludeExistingEntryDiscount(String key) async {
    actions.add('exclude:$key');
  }

  @override
  Future<void> applyDefaultEntryDiscount(String key) async {
    actions.add('apply:$key');
  }

  @override
  Future<void> updateEntryNetAmount(LedgerEntry row, int amount) async {
    actions.add('net:${row.id}:$amount');
  }

  @override
  Future<void> deleteExpense(int id) async {
    actions.add('delete:$id');
  }

  @override
  Future<void> refreshEntriesArea({bool notify = true}) async {
    refreshCalls++;
  }

  @override
  Future<bool> createExpense(
      {required String usagePlace,
      required String usageItem,
      required int amount,
      required bool discountEnabled,
      int? netAmountOverride,
      String? spendingCategory,
      String? entryDate,
      String? candidateRegistrationKey}) {
    submitCalls++;
    return (completion ??= Completer<bool>()).future;
  }
}

bool isRow(Widget w) => w.runtimeType.toString() == '_MonthEntryCard';
Finder get cards => find.byWidgetPredicate(isRow);
Finder card(int id) => find.ancestor(of: find.text('가게 $id'), matching: cards);

class BuildProbe {
  final durations = <int>[];
  final eager = <int>[];
  int rowBuilds = 0;
}

class MeasuredScreen extends MonthEntriesScreen {
  const MeasuredScreen({required super.state, required this.probe});
  final BuildProbe probe;
  @override
  Widget build(BuildContext context) {
    final watch = Stopwatch()..start();
    final view = super.build(context) as ListView;
    watch.stop();
    probe.durations.add(watch.elapsedMicroseconds);
    final delegate = view.childrenDelegate;
    probe.eager.add(delegate is SliverChildListDelegate
        ? delegate.children.where(isRow).length
        : 0);
    return view;
  }
}

Widget host(P101State state, BuildProbe probe) => MaterialApp(
      theme: buildMoneyNoteTheme(),
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context).copyWith(textScaler: TextScaler.noScaling),
        child: child!,
      ),
      home: Scaffold(
          body: RefreshIndicator(
        onRefresh: state.refreshEntriesArea,
        child: AnimatedBuilder(
            animation: state,
            builder: (_, __) => MeasuredScreen(state: state, probe: probe)),
      )),
    );

void viewport(WidgetTester tester) {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(400, 800);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

ScrollPosition position(WidgetTester tester) =>
    tester.state<ScrollableState>(find.byType(Scrollable).first).position;

Future<void> jump(WidgetTester tester, double pixels) async {
  final p = position(tester);
  p.jumpTo(pixels.clamp(0, p.maxScrollExtent));
  await tester.pump();
}

int visibleRows(WidgetTester tester) => cards.evaluate().where((element) {
      final box = element.renderObject;
      if (box is! RenderBox || !box.hasSize) return false;
      return (box.localToGlobal(Offset.zero) & box.size)
          .overlaps(const Rect.fromLTWH(0, 0, 400, 800));
    }).length;

Future<void> reach(WidgetTester tester, int id) async {
  // Actual incremental scrolling, including creation/disposal of offscreen rows.
  await tester.scrollUntilVisible(find.text('가게 $id'), 550,
      scrollable: find.byType(Scrollable).first, maxScrolls: 100);
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  if (Platform.environment['P101_MODE'] == 'benchmark') {
    testWidgets('P1-01 host samples', (tester) async {
      viewport(tester);
      final output = File(Platform.environment['P101_OUTPUT']!);
      final variant = Platform.environment['P101_VARIANT']!;
      final block = int.parse(Platform.environment['P101_BLOCK']!);
      final smoke = Platform.environment['P101_SMOKE'] == '1';
      final all = <Map<String, Object?>>[];
      final previousCallback = debugOnRebuildDirtyWidget;
      BuildProbe? active;
      debugOnRebuildDirtyWidget = (element, builtOnce) {
        if (isRow(element.widget)) active?.rowBuilds++;
        previousCallback?.call(element, builtOnce);
      };
      addTearDown(() => debugOnRebuildDirtyWidget = previousCallback);
      for (final n in [0, 50, 500, 1000, 5000]) {
        final rows =
            fixture(n); // Preparation is outside every measured interval.
        final digest = sha256
            .convert(utf8.encode(jsonEncode(rows
                .map((r) => [
                      r.id,
                      r.entryDate,
                      r.spendingCategory,
                      r.amountValue,
                      r.effectiveAmountValue,
                      r.title,
                      r.usagePlace,
                      r.usageItem,
                      r.sortOrder,
                      r.paymentKey
                    ])
                .toList())))
            .toString();
        for (var i = -5; i < (smoke ? 1 : 20); i++) {
          final state = P101State(rows), probe = BuildProbe();
          active = probe;
          final pump = Stopwatch()..start();
          await tester.pumpWidget(host(state, probe));
          pump.stop();
          final initialBuild = probe.durations.single;
          final eager = probe.eager.single;
          final initialMounted = cards.evaluate().length;
          final initialVisible = visibleRows(tester);
          final initialRowBuilds = probe.rowBuilds;
          final scrollMounted = <int>[], scrollVisible = <int>[];
          final scrolling = Stopwatch()..start();
          for (final offset in [
            240,
            480,
            720,
            960,
            1200,
            960,
            720,
            480,
            240,
            0
          ]) {
            await jump(tester, offset.toDouble());
            scrollMounted.add(cards.evaluate().length);
            scrollVisible.add(visibleRows(tester));
          }
          scrolling.stop();
          final before = probe.durations.length;
          final rebuild = Stopwatch()..start();
          state.changed();
          await tester.pump();
          rebuild.stop();
          expect(probe.durations.length - before, 1);
          expect(tester.takeException(), isNull);
          expect(initialMounted, lessThanOrEqualTo(n));
          if (n >= 50)
            expect(scrollMounted.reduce((a, b) => a > b ? a : b), lessThan(20));
          if (i >= 0)
            all.add({
              'variant': variant,
              'block': block,
              'rows': n,
              'sample': i,
              'fixture_sha256': digest,
              'build_us': initialBuild,
              'eager_cards': eager,
              'pump_us': pump.elapsedMicroseconds,
              'mounted_initial': initialMounted,
              'visible_initial': initialVisible,
              'initial_row_builds': initialRowBuilds,
              'scroll_us': scrolling.elapsedMicroseconds,
              'scroll_mounted': scrollMounted,
              'scroll_visible': scrollVisible,
              'screen_rebuilds': probe.durations.length - before,
              'rebuild_build_us': probe.durations.last,
              'rebuild_pump_us': rebuild.elapsedMicroseconds,
              'row_build_calls_total': probe.rowBuilds,
            });
          await tester.pumpWidget(const SizedBox.shrink());
          state.dispose();
          active = null;
        }
      }
      output.writeAsStringSync(all.map(jsonEncode).join('\n') + '\n');
    }, timeout: const Timeout(Duration(minutes: 15)));
    return;
  }

  testWidgets('P1-01 empty state and server values', (tester) async {
    viewport(tester);
    final state = P101State(fixture(0));
    addTearDown(state.dispose);
    await tester.pumpWidget(host(state, BuildProbe()));
    await tester.scrollUntilVisible(find.text('이번 달 지출 내역이 없습니다.'), 350,
        scrollable: find.byType(Scrollable).first);
    expect(find.text('이번 달 지출 내역이 없습니다.'), findsOneWidget);
    expect(find.text('0건'), findsOneWidget);
    expect(find.text('1,000원'), findsOneWidget);
  });

  testWidgets('P1-01 equal dates, first/last, scroll away and reopen',
      (tester) async {
    viewport(tester);
    final state = P101State(fixture(50));
    addTearDown(state.dispose);
    await tester.pumpWidget(host(state, BuildProbe()));
    await reach(tester, 50);
    final firstState = tester.state(find.descendant(
        of: card(50), matching: find.byType(DropdownButtonFormField<String>)));
    await reach(tester, 1);
    expect(find.text('가게 1'), findsOneWidget);
    await jump(tester, 0);
    await reach(tester, 50);
    expect(find.text('가게 50'), findsOneWidget);
    // Offscreen disposal is allowed; displayed category and identity must survive.
    expect(
        tester
            .widget<DropdownButtonFormField<String>>(find.descendant(
                of: card(50),
                matching: find.byType(DropdownButtonFormField<String>)))
            .initialValue,
        'essential');
    expect(firstState.mounted, isFalse);
  });

  testWidgets('P1-01 long Korean and emoji do not overflow', (tester) async {
    viewport(tester);
    final state = P101State([
      LedgerEntry(
          id: 7,
          bookSection: 'current',
          entryKind: 'expense',
          title: '한글과 🧾☕ 가족👨‍👩‍👧‍👦 ${'긴 사용내역 ' * 12}',
          sortOrder: 1,
          entryDate: '2026-10-03',
          amountValue: 10000,
          usagePlace: '가게 7',
          usageItem: '🍚 긴 사용항목 ' * 12,
          effectiveAmountValue: 7777)
    ]);
    addTearDown(state.dispose);
    await tester.pumpWidget(host(state, BuildProbe()));
    await reach(tester, 7);
    expect(tester.takeException(), isNull);
    expect(find.textContaining('🍚'), findsWidgets);
  });

  testWidgets('P1-01 category and discount target stable after reordering',
      (tester) async {
    viewport(tester);
    final state = P101State(fixture(3));
    addTearDown(state.dispose);
    await tester.pumpWidget(host(state, BuildProbe()));
    await reach(tester, 3);
    final dropdown = find.descendant(
        of: card(3), matching: find.byType(DropdownButtonFormField<String>));
    final retained = tester.state(dropdown);
    await tester.ensureVisible(dropdown);
    await tester.tap(dropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('최소한의 품위유지비').last);
    await tester.pumpAndSettle();
    expect(state.actions.last, 'category:3:dignity');
    state.entries = [
      ...state.entries,
      LedgerEntry(
          id: 99,
          bookSection: 'current',
          entryKind: 'expense',
          title: '추가',
          usagePlace: '가게 99',
          sortOrder: 0,
          entryDate: '2026-10-04',
          amountValue: 10000)
    ];
    state.changed();
    await tester.pump();
    await reach(tester, 3);
    // This additional identity guarantee belongs to the experimental keyed
    // candidate. The preserved eager baseline still tests mutation targeting.
    if (Platform.environment['P101_VARIANT'] == 'candidate') {
      expect(identical(tester.state(dropdown), retained), isTrue);
      expect((tester.state(dropdown) as FormFieldState<String>).value, 'dignity');
    }
    await tester.ensureVisible(dropdown);
    await tester.tap(dropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('안 썼으면 큰일').last);
    await tester.pumpAndSettle();
    expect(state.actions.last, 'category:3:essential');
    final button = find.descendant(of: card(3), matching: find.text('할인 제외'));
    await tester.ensureVisible(button);
    await tester.tap(button);
    await tester.pump();
    expect(state.actions.last, 'exclude:p101-3');
  });

  testWidgets('P1-01 discount apply, net edit and delete target',
      (tester) async {
    viewport(tester);
    final state = P101State([
      LedgerEntry(
          id: 8,
          bookSection: 'current',
          entryKind: 'expense',
          title: '가게 8',
          sortOrder: 1,
          entryDate: '2026-10-03',
          amountValue: 10000,
          paymentKey: 'p101-8',
          discountPolicy: 'enabled',
          automaticDiscountEligible: true,
          discountOverride: 1,
          effectiveAmountValue: 8777)
    ]);
    addTearDown(state.dispose);
    await tester.pumpWidget(host(state, BuildProbe()));
    await reach(tester, 8);
    Future<void> tapInRow(String label) async {
      final f = find.descendant(of: card(8), matching: find.text(label));
      await tester.ensureVisible(f);
      await tester.tap(f);
      await tester.pumpAndSettle();
    }

    await tapInRow('할인 적용');
    expect(state.actions.last, 'apply:p101-8');
    await tapInRow('실결제액 수정');
    final field = find.descendant(
        of: find.byType(AlertDialog), matching: find.byType(TextField));
    expect(tester.widget<TextField>(field).controller!.text, '8777');
    await tester.enterText(field, '8000');
    await tester.tap(find.text('저장'));
    await tester.pumpAndSettle();
    expect(state.actions.last, 'net:8:8000');
    await tapInRow('삭제');
    await tester.tap(find.descendant(
        of: find.byType(AlertDialog), matching: find.text('삭제')));
    await tester.pumpAndSettle();
    expect(state.actions.last, 'delete:8');
  });

  testWidgets('P1-01 pull refresh', (tester) async {
    viewport(tester);
    final state = P101State(fixture(0));
    addTearDown(state.dispose);
    await tester.pumpWidget(host(state, BuildProbe()));
    await tester.drag(find.byType(ListView), const Offset(0, 700));
    await tester.pumpAndSettle();
    expect(state.refreshCalls, 1);
  });

  testWidgets('P1-01 draft, focus, single-flight and newer draft survive',
      (tester) async {
    viewport(tester);
    final state = P101State(fixture(50));
    addTearDown(state.dispose);
    await tester.pumpWidget(host(state, BuildProbe()));
    final form = find.byType(ExpenseInputCard);
    Finder field(String label) => find.descendant(
        of: form,
        matching: find.byWidgetPredicate(
            (w) => w is TextField && w.decoration?.labelText == label));
    await tester.ensureVisible(field('사용처'));
    await tester.enterText(field('사용처'), '보존할 가게');
    await tester.enterText(field('금액'), '500');
    await tester.showKeyboard(field('사용처'));
    await tester.pump();
    final focus = tester.widget<TextField>(field('사용처')).focusNode!;
    expect(focus.hasFocus, isTrue);
    state.changed();
    await tester.pump();
    expect(focus.hasFocus, isTrue);
    await jump(tester, 1800);
    await jump(tester, 200);
    expect(tester.widget<TextField>(field('사용처')).controller!.text, '보존할 가게');
    expect(focus.hasFocus, isTrue);
    final submit = find.descendant(of: form, matching: find.text('지출 추가'));
    await tester.ensureVisible(submit);
    await tester.tap(submit);
    // Re-entry through the still-existing keyboard callback must be single-flight.
    tester.widget<TextField>(field('금액')).onSubmitted!('500');
    expect(state.submitCalls, 1);
    await tester.enterText(field('금액'), '700');
    state.completion!.complete(true);
    await tester.pumpAndSettle();
    expect(tester.widget<TextField>(field('금액')).controller!.text, '700');
  });

  testWidgets('P1-01 offline controls disabled and values estimated',
      (tester) async {
    viewport(tester);
    final state = P101State(fixture(1))
      ..connectivityMode = ConnectivityMode.offline;
    addTearDown(state.dispose);
    await tester.pumpWidget(host(state, BuildProbe()));
    expect(find.text('월 지출(예상)'), findsOneWidget);
    await reach(tester, 1);
    expect(
        tester
            .widget<DropdownButtonFormField<String>>(find.descendant(
                of: card(1),
                matching: find.byType(DropdownButtonFormField<String>)))
            .onChanged,
        isNull);
    for (final button in tester.widgetList<OutlinedButton>(
        find.descendant(of: card(1), matching: find.byType(OutlinedButton)))) {
      expect(button.onPressed, isNull);
    }
    expect(find.descendant(of: card(1), matching: find.text('실결제 9,880원')),
        findsOneWidget);
  });
}
