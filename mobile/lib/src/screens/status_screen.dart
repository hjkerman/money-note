import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

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
                child: Text('상태',
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
        MoneyCard(
          color: moneyGreenSoft,
          child: Text(
            state.judgment?.budget.message.isNotEmpty == true
                ? state.judgment!.budget.message
                : '관리 가능한 구간입니다.',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
          ),
        ),
        const SectionTitle('주요 조작'),
        Row(
          children: [
            Expanded(
                child: ElevatedButton(
                    onPressed: state.isBusy ? null : state.refresh,
                    child: const Text('동기화'))),
            const SizedBox(width: 10),
            const Expanded(
              child: OutlinedButton(onPressed: null, child: Text('스냅샷 다운로드')),
            ),
          ],
        ),
        const SectionTitle('고급 기능'),
        const MoneyCard(
          child: Text(
              '월마감, 백업, 복원, 관리 로그, 설정은 모바일에서도 접근 가능하게 두되 일상 입력 흐름과 분리합니다.'),
        ),
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
