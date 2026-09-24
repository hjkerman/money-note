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
    if (state.isPersistenceRecoveryBlocked) {
      return _PersistenceRecoveryBlockedView(state: state);
    }
    if (state.serverFailurePromptPending) {
      return _ServerUnavailableView(state: state);
    }
    if (state.isReconciliationRequired) {
      return _ReconciliationRequiredView(state: state);
    }
    if (state.isReconciliationFinalizing) {
      return _ReconciliationFinalizingView(state: state);
    }
    if (!state.isLoggedIn) {
      return LoginScreen(state: state);
    }
    return HomeShell(state: state);
  }
}

class _PersistenceRecoveryBlockedView extends StatelessWidget {
  const _PersistenceRecoveryBlockedView({required this.state});

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
                const Icon(Icons.lock_outline, size: 52),
                const SizedBox(height: 14),
                const Text(
                  '오프라인 저장소 복구가 필요합니다',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 10),
                const Text(
                  '기존 baseline 또는 journal을 안전하게 해석할 수 없어 금융 작업을 차단했습니다. 저장 파일을 덮어쓰거나 삭제하지 않습니다.',
                  textAlign: TextAlign.center,
                ),
                if (state.offlineEntryMessage.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(state.offlineEntryMessage,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.red)),
                ],
                const SizedBox(height: 20),
                const OutlinedButton(
                  onPressed: SystemNavigator.pop,
                  child: Text('앱 종료'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
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
                const OutlinedButton(
                  onPressed: SystemNavigator.pop,
                  child: Text('앱 종료'),
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
                  if (state.reconciliationServerChanged) ...[
                    const SizedBox(height: 8),
                    const Text(
                      '오프라인 모드 시작 이후 서버 데이터도 변경되었습니다.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.red,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                  if (state.reconciliationRecoveryReady) ...[
                    const SizedBox(height: 14),
                    FilledButton.tonal(
                      onPressed: state.isBusy
                          ? null
                          : () => choice == ReconciliationChoice.applyToServer
                              ? _confirmMobileWins(context)
                              : _confirmServerWins(context),
                      child: Text(
                        choice == ReconciliationChoice.applyToServer
                            ? 'Mobile Wins 최종 실행'
                            : 'Server Wins 최종 실행',
                      ),
                    ),
                  ],
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _confirmMobileWins(BuildContext context) async {
    final confirmed = await _confirm(
      context,
      title: 'Mobile Wins를 실행할까요?',
      message: '서버의 현재 상태 대신 오프라인 진입 직전 기준 B를 복원하고 '
          '오프라인 journal J를 원래 순서대로 적용합니다. 서버에서 별도로 발생한 변경은 사라질 수 있습니다.',
      confirmLabel: 'Mobile Wins 계속',
    );
    if (!confirmed || !context.mounted) return;
    if (state.reconciliationServerChanged) {
      final conflictConfirmed = await _confirm(
        context,
        title: '서버 변경도 덮어쓸까요?',
        message: '오프라인 모드 시작 이후 서버 데이터도 변경되었습니다. '
            '계속하면 결과는 현재 서버 S + J가 아니라 Apply(B, J)입니다.',
        confirmLabel: '서버 변경을 덮어쓰기',
      );
      if (!conflictConfirmed || !context.mounted) return;
    }
    final password = await _password(context);
    if (password == null || password.isEmpty) return;
    await state.reconcileMobileWins(
      password: password,
      confirmServerChanged: state.reconciliationServerChanged,
    );
  }

  Future<void> _confirmServerWins(BuildContext context) async {
    final confirmed = await _confirm(
      context,
      title: 'Server Wins를 실행할까요?',
      message: '오프라인 journal을 서버에 적용하지 않고 현재 서버 상태로 모바일을 다시 만듭니다. '
          '검증된 mobile recovery bundle은 보존됩니다.',
      confirmLabel: 'Server Wins 실행',
    );
    if (!confirmed) return;
    await state.reconcileServerWins();
  }

  Future<bool> _confirm(
    BuildContext context, {
    required String title,
    required String message,
    required String confirmLabel,
  }) async {
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(title),
            content: Text(message),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('취소'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(confirmLabel),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<String?> _password(BuildContext context) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('현재 비밀번호 확인'),
        content: TextField(
          controller: controller,
          obscureText: true,
          autofocus: true,
          decoration: const InputDecoration(labelText: '비밀번호'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('확인'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }
}

class _ReconciliationFinalizingView extends StatelessWidget {
  const _ReconciliationFinalizingView({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final committed = state.mobileCommitIsCommitted;
    final serverWins = state.isServerWinsFinalizing;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.sync_lock, size: 52),
                const SizedBox(height: 14),
                Text(
                  serverWins
                      ? '서버 상태 동기화를 기다리고 있습니다'
                      : committed
                          ? '서버 반영은 완료되었습니다'
                          : '조정 결과를 확인하고 있습니다',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  serverWins
                      ? '현재 authoritative 서버 상태를 다시 받아 모바일과 새 baseline을 만듭니다. '
                          '완료 전에는 journal을 보존하고 ONLINE으로 전환하지 않습니다.'
                      : committed
                          ? '최신 authoritative 상태를 받아 새 baseline을 만드는 중입니다. '
                              '완료 전에는 ONLINE으로 전환하지 않습니다.'
                          : '같은 reconciliation ID로 서버 commit 여부를 확인합니다. '
                              '오프라인 journal은 다시 replay하지 않습니다.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                Text(
                  state.statusMessage,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: state.isBusy
                      ? null
                      : () => state.resumeReconciliationFinalization(),
                  child: const Text('상태 확인 및 동기화 재시도'),
                ),
                if (state.mobileCommitIsUnknown) ...[
                  const SizedBox(height: 10),
                  OutlinedButton(
                    onPressed:
                        state.isBusy ? null : () => _retryWithPassword(context),
                    child: const Text('선택한 Mobile Wins 재시도'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _retryWithPassword(BuildContext context) async {
    final controller = TextEditingController();
    final password = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('같은 Mobile Wins 재시도'),
        content: TextField(
          controller: controller,
          obscureText: true,
          autofocus: true,
          decoration: const InputDecoration(labelText: '현재 비밀번호'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('재시도'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (password == null || password.isEmpty) return;
    await state.resumeReconciliationFinalization(password: password);
  }
}
