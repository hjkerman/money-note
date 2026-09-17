import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'api_client.dart';
import 'app_state.dart';
import 'offline/offline_data.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';
import 'theme.dart';

class MoneyNoteApp extends StatefulWidget {
  const MoneyNoteApp({
    super.key,
    this.stateOverride,
    this.bootstrapOnStart = true,
  });

  final AppState? stateOverride;
  final bool bootstrapOnStart;

  @override
  State<MoneyNoteApp> createState() => _MoneyNoteAppState();
}

class _MoneyNoteAppState extends State<MoneyNoteApp>
    with WidgetsBindingObserver {
  late final AppState state;
  late final bool _ownsState;
  bool _wasInBackground = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _ownsState = widget.stateOverride == null;
    state = widget.stateOverride ?? AppState(MoneyNoteApiClient());
    if (widget.bootstrapOnStart) state.bootstrap();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    if (_ownsState) state.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState lifecycleState) {
    if (lifecycleState == AppLifecycleState.paused ||
        lifecycleState == AppLifecycleState.hidden ||
        lifecycleState == AppLifecycleState.detached) {
      _wasInBackground = true;
      return;
    }
    if (lifecycleState == AppLifecycleState.resumed && _wasInBackground) {
      _wasInBackground = false;
      unawaited(state.resumeFromBackground());
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        return MaterialApp(
          title: 'Money-Note',
          debugShowCheckedModeBanner: false,
          theme: buildMoneyNoteTheme(),
          home: _homeForState(),
        );
      },
    );
  }

  Widget _homeForState() {
    if (state.isBootstrapping) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (state.serverFailurePromptPending) {
      return _ServerUnavailableView(state: state);
    }
    if (state.isReconciliationRequired) {
      return _ReconciliationRequiredView(state: state);
    }
    if (!state.isLoggedIn) {
      return LoginScreen(state: state);
    }
    return HomeShell(state: state);
  }
}

class _ServerUnavailableView extends StatelessWidget {
  const _ServerUnavailableView({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  '서버에 연결할 수 없습니다.\n오프라인 모드로 사용하시겠습니까?',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
                ),
                if (state.offlineEntryMessage.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    state.offlineEntryMessage,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.red),
                  ),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: state.isBusy ? null : state.enterOfflineMode,
                  child: const Text('오프라인 모드 사용'),
                ),
                const SizedBox(height: 10),
                OutlinedButton(
                  onPressed: SystemNavigator.pop,
                  child: const Text('앱 종료'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ReconciliationRequiredView extends StatelessWidget {
  const _ReconciliationRequiredView({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final choice = state.reconciliationChoice;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.sync_problem, size: 52),
                const SizedBox(height: 14),
                const Text(
                  '서버 연결이 복구되었습니다',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 10),
                Text(
                  '오프라인 변경 ${state.pendingOfflineOperationCount}건이 있습니다. '
                  '조정 방식을 선택하기 전에는 읽기 전용입니다.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: state.isBusy
                      ? null
                      : () => state.selectReconciliationChoice(
                            ReconciliationChoice.applyToServer,
                          ),
                  child: const Text('오프라인 변경사항을 서버에 적용'),
                ),
                const SizedBox(height: 10),
                OutlinedButton(
                  onPressed: state.isBusy
                      ? null
                      : () => state.selectReconciliationChoice(
                            ReconciliationChoice.discardAndUseServer,
                          ),
                  child: const Text('오프라인 변경사항을 폐기하고 서버 데이터 사용'),
                ),
                if (choice != null) ...[
                  const SizedBox(height: 18),
                  Text(
                    state.statusMessage,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Phase 1에서는 선택과 안전 경계만 저장합니다. '
                    '실제 replay 또는 폐기는 Phase 2에서 수행합니다.',
                    textAlign: TextAlign.center,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
