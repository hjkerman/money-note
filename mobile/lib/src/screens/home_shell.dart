import 'package:flutter/material.dart';

import '../app_state.dart';
import '../theme.dart';
import 'cash_flow_screen.dart';
import 'family_screen.dart';
import 'input_screen.dart';
import 'month_entries_screen.dart';
import 'status_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({required this.state, super.key});

  final AppState state;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [
      InputScreen(state: widget.state),
      CashFlowScreen(state: widget.state),
      MonthEntriesScreen(state: widget.state),
      FamilyScreen(state: widget.state),
      StatusScreen(state: widget.state),
    ];

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: widget.state.refresh,
        child: screens[index],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        indicatorColor: moneyGreenSoft,
        onDestinationSelected: (value) => setState(() => index = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.add_card), label: '입력'),
          NavigationDestination(
              icon: Icon(Icons.account_balance_wallet), label: '현금'),
          NavigationDestination(icon: Icon(Icons.receipt_long), label: '내역'),
          NavigationDestination(icon: Icon(Icons.people_alt), label: '가족'),
          NavigationDestination(icon: Icon(Icons.assessment), label: '상태'),
        ],
      ),
    );
  }
}
