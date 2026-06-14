import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../app_state.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({required this.state, super.key});

  final AppState state;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final username = TextEditingController();
  final password = TextEditingController();

  @override
  void dispose() {
    username.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              const Text('Money-Note',
                  style: TextStyle(fontSize: 38, fontWeight: FontWeight.w900)),
              const SizedBox(height: 10),
              const Text('카드 긁은 죄를 10초 안에 자백하는 장부입니다.',
                  style: TextStyle(color: moneyMuted, fontSize: 16)),
              const SizedBox(height: 28),
              MoneyCard(
                child: AutofillGroup(
                  child: Column(
                    children: [
                      TextField(
                        controller: username,
                        autofillHints: const [AutofillHints.username],
                        keyboardType: TextInputType.text,
                        textInputAction: TextInputAction.next,
                        decoration: const InputDecoration(labelText: '아이디'),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: password,
                        autofillHints: const [AutofillHints.password],
                        obscureText: true,
                        textInputAction: TextInputAction.done,
                        decoration: const InputDecoration(labelText: '비밀번호'),
                        onSubmitted: (_) => _submit(),
                      ),
                      const SizedBox(height: 18),
                      ElevatedButton(
                        onPressed: widget.state.isBusy ? null : _submit,
                        child: const Text('로그인'),
                      ),
                    ],
                  ),
                ),
              ),
              if (widget.state.statusMessage.isNotEmpty) ...[
                const SizedBox(height: 14),
                Text(widget.state.statusMessage,
                    style: const TextStyle(color: moneyRed)),
              ],
              const Spacer(flex: 2),
            ],
          ),
        ),
      ),
    );
  }

  void _submit() {
    TextInput.finishAutofillContext();
    widget.state.login(username.text.trim(), password.text);
  }
}
