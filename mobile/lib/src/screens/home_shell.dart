import 'package:flutter/material.dart';

import '../app_state.dart';
import '../theme.dart';
import 'family_screen.dart';
import 'input_screen.dart';
import 'payment_screen.dart';
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
      PaymentScreen(state: widget.state),
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
          NavigationDestination(icon: Icon(Icons.credit_card), label: '결제'),
          NavigationDestination(icon: Icon(Icons.people_alt), label: '가족'),
          NavigationDestination(icon: Icon(Icons.assessment), label: '상태'),
        ],
      ),
    );
  }
}
