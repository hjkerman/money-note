import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/screens/month_entries_screen.dart';

import 'offline_widget_submit_test.dart' show FormAppStateFake;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final cases = <(String, String, Map<String, dynamic>, bool, bool)>[
    ('transport', '일반 가맹점', {'is_transport': true, 'is_toll': false}, true, false),
    ('toll', '일반 가맹점', {'is_transport': false, 'is_toll': true}, false, true),
    ('ordinary', '일반 가맹점', {'is_transport': false, 'is_toll': false}, false, false),
    ('keywords', '지하철 버스 교통 하이패스 고속도로 통행료', {'is_transport': false, 'is_toll': false}, false, false),
    ('absent defaults', '지하철 하이패스 통행료', {}, false, false),
    ('null defaults', '버스 통행료', {'is_transport': null, 'is_toll': null}, false, false),
    ('both flags', '일반 가맹점', {'is_transport': true, 'is_toll': true}, true, true),
  ];
  for (final (name, title, flags, transport, toll) in cases) {
    testWidgets('monthly badges use server booleans: $name', (tester) async {
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = const Size(1200, 2000);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final entry = LedgerEntry.fromJson({
        'id': 41,
        'book_section': 'current',
        'entry_kind': 'expense',
        'title': title,
        'usage_place': title,
        'sort_order': 1,
        'entry_date': '2026-10-03',
        'amount_value': 10000,
        'discount_override': 0,
        ...flags,
      });
      expect(entry.isTransport, transport);
      expect(entry.isToll, toll);
      final state = FormAppStateFake()..entries = [entry];
      addTearDown(state.dispose);
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: MonthEntriesScreen(state: state)),
      ));
      await tester.pumpAndSettle();
      expect(find.text('교통'), transport ? findsOneWidget : findsNothing);
      expect(find.text('통행료'), toll ? findsOneWidget : findsNothing);
      expect(find.text(title), findsOneWidget);
    });
  }
}
