import 'package:flutter/material.dart';

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

class _MoneyNoteAppState extends State<MoneyNoteApp> {
  late final AppState state;

  @override
  void initState() {
    super.initState();
    state = AppState(MoneyNoteApiClient());
    state.bootstrap();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        return MaterialApp(
          title: '머니 노트',
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
    if (!state.isLoggedIn) {
      return LoginScreen(state: state);
    }
    return HomeShell(state: state);
  }
}
