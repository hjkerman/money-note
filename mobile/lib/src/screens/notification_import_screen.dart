import 'package:flutter/material.dart';

import '../theme.dart';
import '../widgets/money_card.dart';

class NotificationImportScreen extends StatelessWidget {
  const NotificationImportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('알림에서 가져오기')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: const [
          MoneyCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('카드사 알림 보관함',
                    style:
                        TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
                SizedBox(height: 10),
                Text(
                  '아직 납치한 카드사 푸시 알림이 없습니다. 훗날 이곳에서 알림을 확인하고 지출로 편입합니다.',
                  style:
                      TextStyle(color: moneyMuted, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
