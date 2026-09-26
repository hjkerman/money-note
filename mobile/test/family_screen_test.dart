import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/screens/family_screen.dart';
import 'package:money_note_mobile/src/theme.dart';

class _PanelState extends AppState {
  _PanelState() : super(MoneyNoteApiClient(baseUrl: 'https://example.invalid'));

  final calls = <String>[];
  final pending = <Completer<bool>>[];

  @override
  Future<bool> createPanel({
    required String panelType,
    required String title,
    required int amount,
    bool discountEnabled = true,
    String? spentOn,
    String? candidateRegistrationKey,
    String? manualRegistrationKey,
  }) {
    calls.add(
        '$panelType|$title|$amount|$discountEnabled|$manualRegistrationKey');
    final completer = Completer<bool>();
    pending.add(completer);
    return completer.future;
  }
}

void main() {
  Future<void> show(WidgetTester tester, _PanelState state) async {
    await tester.pumpWidget(MaterialApp(
      theme: buildMoneyNoteTheme(),
      home: Scaffold(body: FamilyScreen(state: state)),
    ));
    expect(tester.takeException(), isNull);
  }

  testWidgets('settlement screen renders without a Material assertion',
      (tester) async {
    await show(tester, _PanelState());
    expect(find.text('정산'), findsOneWidget);
    expect(find.text('할인 적용'), findsOneWidget);
  });

  testWidgets('failed 500 draft survives; button and keyboard share one flight',
      (tester) async {
    final state = _PanelState();
    await show(tester, state);
    await tester.enterText(find.byType(TextField).at(0), '생활비');
    await tester.enterText(find.byType(TextField).at(1), '500');
    await tester.ensureVisible(find.text('청구 추가'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('청구 추가'));
    await tester.pump();
    tester.widget<TextField>(find.byType(TextField).at(1)).onSubmitted!('500');
    await tester.pump();
    expect(state.calls, hasLength(1));
    state.pending.single.complete(false);
    await tester.pump();
    expect(find.text('500'), findsOneWidget);
    await tester.tap(find.text('청구 추가'));
    await tester.pump();
    expect(state.calls, hasLength(2));
    expect(state.calls[1], state.calls[0]);
    state.pending.last.complete(true);
    await tester.pump();
    expect(find.text('500'), findsNothing);
  });

  testWidgets('late success or failure cannot clear newer 700 draft',
      (tester) async {
    for (final success in [true, false]) {
      final state = _PanelState();
      await show(tester, state);
      await tester.enterText(find.byType(TextField).at(0), '생활비');
      await tester.enterText(find.byType(TextField).at(1), '500');
      await tester.ensureVisible(find.text('청구 추가'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('청구 추가'));
      await tester.pump();
      await tester.enterText(find.byType(TextField).at(1), '700');
      state.pending.single.complete(success);
      await tester.pump();
      expect(find.text('700'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    }
  });
}
