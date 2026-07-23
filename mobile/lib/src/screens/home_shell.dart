import 'dart:async';

import 'package:flutter/material.dart';

import '../app_state.dart';
import '../theme.dart';
import 'cash_flow_screen.dart';
import 'family_screen.dart';
import 'input_screen.dart';
import 'month_entries_screen.dart';
import 'notification_import_screen.dart';
import 'status_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({required this.state, super.key});

  final AppState state;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;
  late final PageController _pageController;
  late int _seenNotificationImportOpenGeneration;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _seenNotificationImportOpenGeneration =
        widget.state.notificationImportOpenGeneration;
    if (_seenNotificationImportOpenGeneration > 0) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _openNotificationImport();
      });
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant HomeShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_seenNotificationImportOpenGeneration !=
        widget.state.notificationImportOpenGeneration) {
      _seenNotificationImportOpenGeneration =
          widget.state.notificationImportOpenGeneration;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _openNotificationImport();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      HomeScreen(
        state: widget.state,
        onJudgmentTap: () => _selectTab(4),
        onManualInputTap: () => _selectTab(2),
      ),
      FamilyScreen(state: widget.state),
      MonthEntriesScreen(state: widget.state),
      CashFlowScreen(state: widget.state),
      StatusScreen(state: widget.state),
    ];

    return Scaffold(
      body: PageView(
        controller: _pageController,
        onPageChanged: (value) => unawaited(_handlePageChanged(value)),
        children: [
          for (var screenIndex = 0;
              screenIndex < screens.length;
              screenIndex += 1)
            _bodyForIndex(screens[screenIndex], screenIndex),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        indicatorColor: moneyGreenSoft,
        onDestinationSelected: _selectTab,
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home), label: '홈'),
          NavigationDestination(icon: Icon(Icons.people_alt), label: '정산'),
          NavigationDestination(icon: Icon(Icons.add_card), label: '입력'),
          NavigationDestination(
              icon: Icon(Icons.account_balance_wallet), label: '현금'),
          NavigationDestination(icon: Icon(Icons.settings), label: '설정'),
        ],
      ),
    );
  }

  Widget _bodyForIndex(Widget screen, int screenIndex) {
    if (screenIndex == 4) return screen;
    return RefreshIndicator(
      onRefresh: () => _refreshForIndex(screenIndex),
      child: screen,
    );
  }

  Future<void> _refreshForIndex(int screenIndex) {
    return switch (screenIndex) {
      0 => widget.state.refreshInputArea(),
      1 => widget.state.refreshSettlementArea(),
      2 => widget.state.refreshEntriesArea(),
      3 => widget.state.refreshCashArea(),
      _ => widget.state.refresh(),
    };
  }

  Future<void> _selectTab(int value) async {
    if (value == index) return;
    await _pageController.animateToPage(
      value,
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeOutCubic,
    );
  }

  Future<void> _handlePageChanged(int value) async {
    if (value == index) return;
    setState(() => index = value);
    if (value == 4) {
      await widget.state.refresh();
      return;
    }
    await _refreshForIndex(value);
  }

  void _openNotificationImport() {
    if (index != 0) {
      _pageController.jumpToPage(0);
    }
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => NotificationImportScreen(state: widget.state),
      ),
    );
  }
}
