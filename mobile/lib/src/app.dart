import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'api_client.dart';
import 'app_state.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';
import 'theme.dart';

class MoneyNoteApp extends StatefulWidget {
  const MoneyNoteApp({super.key});

  @override
  State<MoneyNoteApp> createState() => _MoneyNoteAppState();
}

class _MoneyNoteAppState extends State<MoneyNoteApp>
    with WidgetsBindingObserver {
  late final AppState state;
  final GlobalKey<NavigatorState> _navigatorKey = GlobalKey<NavigatorState>();
  bool _wasInBackground = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    state = AppState(MoneyNoteApiClient());
    state.bootstrap();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    state.dispose();
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
      unawaited(_resumeFromBackground());
    }
  }

  Future<void> _resumeFromBackground() async {
    await state.resumeFromBackground();
    if (!mounted) return;
    _navigatorKey.currentState?.popUntil((route) => route.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        return MaterialApp(
          title: 'Money-Note',
          debugShowCheckedModeBanner: false,
          navigatorKey: _navigatorKey,
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
    if (state.networkUnavailable) {
      return const _NetworkRequiredView();
    }
    if (!state.isLoggedIn) {
      return LoginScreen(state: state);
    }
    return HomeShell(state: state);
  }
}

class _NetworkRequiredView extends StatelessWidget {
  const _NetworkRequiredView();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('서버에 연결할 수 없습니다.',
                    textAlign: TextAlign.center,
                    style:
                        TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
                SizedBox(height: 12),
                Text(
                  'Money-Note 모바일 앱은 서버 DB를 원본으로 사용합니다. 네트워크 연결이나 서버 상태를 확인한 뒤 다시 실행해 주세요.',
                  textAlign: TextAlign.center,
                ),
                SizedBox(height: 20),
                FilledButton(
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
