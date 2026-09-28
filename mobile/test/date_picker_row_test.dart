import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/widgets/date_picker_row.dart';

void main() {
  testWidgets('shared date row preserves display, range, and ISO callback',
      (tester) async {
    String? selected;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: DatePickerRow(
          label: '사용일',
          value: '2026-09-17',
          onChanged: (value) => selected = value,
        ),
      ),
    ));

    expect(find.text('사용일'), findsOneWidget);
    expect(find.text('09/17'), findsOneWidget);
    await tester.tap(find.text('사용일'));
    await tester.pumpAndSettle();

    final picker = tester.widget<DatePickerDialog>(find.byType(DatePickerDialog));
    expect(picker.firstDate, DateTime(2020, 1, 1));
    expect(picker.lastDate, DateTime(2100, 12, 31));
    expect(picker.initialDate, DateTime(2026, 9, 17));
    await tester.tap(find.text('18'));
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    expect(selected, '2026-09-18');
  });
}
