import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'management_screen.dart';

class StatusScreen extends StatelessWidget {
  const StatusScreen({required this.state, super.key});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final summary = state.summary;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        Row(
          children: [
            const Expanded(
                child: Text('설정',
                    style:
                        TextStyle(fontSize: 24, fontWeight: FontWeight.w900))),
            IconButton(
                onPressed: state.isBusy ? null : state.logout,
                icon: const Icon(Icons.logout),
                tooltip: '로그아웃'),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
                child:
                    AmountTile(label: '카드대금', amount: won(summary?.cardTotal))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(label: '월 지출', amount: won(_expenseTotal()))),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
                child: AmountTile(
                    label: '익월 유동성', amount: won(summary?.nextMonthLiquidity))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(
                    label: '동결', amount: won(summary?.frozenAssetTotal))),
          ],
        ),
        const SectionTitle('예산심사위원회'),
        _JudgmentCard(
          title: '예산심사위원회',
          message: state.judgment?.budget.message ?? '',
          color: moneyGreenSoft,
        ),
        const SizedBox(height: 10),
        _JudgmentCard(
          title: '카드 한도 감시',
          message: state.judgment?.credit.message ?? '',
        ),
        const SizedBox(height: 10),
        _JudgmentCard(
          title: '파산심사위원회',
          message: state.judgment?.payment.message ?? '',
        ),
        const SectionTitle('관리'),
        ManagementMenuList(state: state),
        if (state.statusMessage.isNotEmpty) ...[
          const SizedBox(height: 14),
          Text(state.statusMessage, style: const TextStyle(color: moneyMuted)),
        ],
      ],
    );
  }

  int _expenseTotal() {
    return state.expenseEntries
        .fold(0, (sum, entry) => sum + (entry.amountValue ?? 0));
  }
}

class _JudgmentCard extends StatelessWidget {
  const _JudgmentCard({
    required this.title,
    required this.message,
    this.color,
  });

  final String title;
  final String message;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return MoneyCard(
      color: color ?? moneySurface,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style:
                  const TextStyle(fontSize: 15, fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          Text(
            message.trim().isEmpty ? '판단 결과를 불러오는 중입니다.' : message.trim(),
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}
