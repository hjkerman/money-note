part of 'management_screen.dart';

class MonthCloseManagementScreen extends StatelessWidget {
  const MonthCloseManagementScreen({required this.state, super.key});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final status = state.monthCloseStatus;
    final canClose = status?.canClose ?? false;
    return Scaffold(
      appBar: AppBar(title: const Text('월마감')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
        children: [
          MoneyCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Line(label: '서버 기준 날짜', value: status?.calendarDate ?? '-'),
                _Line(label: '마감 대상', value: status?.oldestOpenMonth ?? '-'),
                _Line(label: '마감 가능', value: state.isOnline && canClose ? '가능' : '사용 불가'),
                const SizedBox(height: 12),
                Text(
                  !state.isOnline
                      ? '월마감은 온라인에서만 사용할 수 있습니다.'
                      : canClose
                      ? '월마감은 복원 전 백업을 먼저 남긴 뒤 실행됩니다.'
                      : '월마감은 서버 기준으로 가능한 때에만 사용할 수 있습니다.',
                  style: const TextStyle(
                      color: moneyMuted, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          FilledButton(
            onPressed: !state.canUseOnlineWrites || !canClose
                ? null
                : () => _confirmMonthClose(context),
            child: const Text('월마감 실행'),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmMonthClose(BuildContext context) async {
    final status = state.monthCloseStatus;
    final targetMonth = status?.oldestOpenMonth;
    final isEarlyClose = status?.isEarlyClose ?? false;
    final firstConfirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('월마감'),
        content: Text(targetMonth == null
            ? '현재 열린 월을 마감할까요?'
            : '$targetMonth 기록을 월마감할까요?'),
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
    final unconfirmed = status?.unconfirmedRecurringItems ?? const [];
    final warningText = unconfirmed.map((item) {
      final kind = item.kind == 'fixed' ? '현금' : '카드';
      final detail = item.detail.isEmpty ? '' : ' / ${item.detail}';
      return '[$kind] ${item.title}$detail: ${won(item.amountValue)}';
    }).join('\n');
    final finalConfirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(unconfirmed.isEmpty ? '정말 월마감' : '미확인 정기지출'),
        content: Text(
          unconfirmed.isEmpty
              ? '마감 후에는 이번 달 기록이 전체 기록으로 이동합니다. 정말 진행할까요?'
              : '아직 확인하지 않은 정기지출이 있습니다.\n\n$warningText\n\n먼저 확인하는 것을 권장합니다. 그래도 월마감할까요?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(unconfirmed.isEmpty ? '마감 실행' : '그래도 월마감'),
          ),
        ],
      ),
    );
    if (finalConfirmed == true && targetMonth != null) {
      await state.closeCurrentMonth(
        targetMonth: targetMonth,
        allowEarlyClose: isEarlyClose,
        allowUnconfirmedRecurring: unconfirmed.isNotEmpty,
      );
    }
  }
}

class _Line extends StatelessWidget {
  const _Line({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(label,
              style: const TextStyle(
                  color: moneyMuted, fontWeight: FontWeight.w700)),
          const Spacer(),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}
