import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'snapshot_manager_screen.dart';

class StatusScreen extends StatelessWidget {
  const StatusScreen({required this.state, super.key});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final summary = state.summary;
    final canCloseMonth = _isMonthEnd(DateTime.now());
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
        const SectionTitle('고급 기능'),
        MoneyCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '일상 입력과 분리해둔 조작입니다. 화면을 아래로 당기면 최신 장부를 다시 불러옵니다.',
                style:
                    TextStyle(color: moneyMuted, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 14),
              OutlinedButton(
                onPressed: state.isBusy
                    ? null
                    : () => Navigator.of(context).push(
                          MaterialPageRoute(
                              builder: (_) =>
                                  SnapshotManagerScreen(state: state)),
                        ),
                child: const Text('스냅샷 관리'),
              ),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: state.isBusy || !canCloseMonth
                    ? null
                    : () => _confirmMonthClose(context),
                child: const Text('월마감'),
              ),
              if (!canCloseMonth) ...[
                const SizedBox(height: 8),
                const Text('월마감은 월말에만 사용할 수 있습니다.',
                    style: TextStyle(color: moneyMuted, fontSize: 13)),
              ],
            ],
          ),
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

  Future<void> _confirmMonthClose(BuildContext context) async {
    final firstConfirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('월마감'),
        content: const Text('현재 열린 월을 마감할까요? 서버가 복원 전 백업을 먼저 남깁니다.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('계속'),
          ),
        ],
      ),
    );
    if (firstConfirmed != true || !context.mounted) return;

    final finalConfirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('정말 월마감'),
        content: const Text('마감 후에는 이번 달 기록이 전체 기록으로 이동합니다. 정말 진행할까요?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('마감 실행'),
          ),
        ],
      ),
    );
    if (finalConfirmed == true) {
      await state.closeCurrentMonth();
    }
  }

  bool _isMonthEnd(DateTime value) {
    final tomorrow = value.add(const Duration(days: 1));
    return tomorrow.month != value.month;
  }
}
