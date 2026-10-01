part of 'management_screen.dart';

class PlannedEntryManagementScreen extends StatefulWidget {
  const PlannedEntryManagementScreen({required this.state, super.key});

  final AppState state;

  @override
  State<PlannedEntryManagementScreen> createState() =>
      _PlannedEntryManagementScreenState();
}

class _PlannedEntryManagementScreenState
    extends State<PlannedEntryManagementScreen> {
  final dueDay = TextEditingController();
  final usagePlace = TextEditingController();
  final usageItem = TextEditingController();
  final amount = TextEditingController();
  bool _submitInFlight = false;

  @override
  void dispose() {
    dueDay.dispose();
    usagePlace.dispose();
    usageItem.dispose();
    amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.state,
      builder: (context, _) {
        final rows = widget.state.plannedEntries;
        final confirmedRows = widget.state.confirmedPlannedEntries;
        final total = [...rows, ...confirmedRows]
            .fold<int>(0, (sum, entry) => sum + (entry.amountValue ?? 0));
        return Scaffold(
          appBar: AppBar(title: const Text('카드 정기결제')),
          body: RefreshIndicator(
            onRefresh: widget.state.refreshPlannedManagementArea,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
              children: [
                AmountTile(label: '예정액', amount: won(total)),
                const SectionTitle('등록'),
                MoneyCard(
                  child: Column(
                    children: [
                      TextField(
                        controller: dueDay,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: '결제일'),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                          controller: usagePlace,
                          decoration: const InputDecoration(labelText: '사용처')),
                      const SizedBox(height: 12),
                      TextField(
                          controller: usageItem,
                          decoration: const InputDecoration(labelText: '세부내역')),
                      const SizedBox(height: 12),
                      TextField(
                        controller: amount,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: '금액'),
                        onSubmitted: (_) => _submit(),
                      ),
                      const SizedBox(height: 14),
                      ElevatedButton(
                          onPressed: widget.state.canUseOnlineWrites &&
                                  !_submitInFlight
                              ? _submit
                              : null,
                          child: const Text('정기결제 추가')),
                    ],
                  ),
                ),
                SectionTitle('목록',
                    trailing: Text('${rows.length}건',
                        style: const TextStyle(color: moneyMuted))),
                if (rows.isEmpty)
                  const MoneyCard(child: Text('카드 정기결제가 없습니다.')),
                ...rows.map((entry) => _PlannedEntryItem(
                      key: ValueKey('planned-recurring-${entry.id}'),
                      entry: entry,
                      state: widget.state,
                    )),
                SectionTitle('이번 달 확인 처리됨',
                    trailing: Text('${confirmedRows.length}건',
                        style: const TextStyle(color: moneyMuted))),
                if (confirmedRows.isEmpty)
                  const MoneyCard(child: Text('이번 달에 확인 처리된 정기결제가 없습니다.')),
                ...confirmedRows
                    .map((entry) => _ConfirmedPlannedEntryItem(entry: entry)),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _submit() async {
    if (_submitInFlight) return;
    final submittedDueDay = dueDay.text;
    final submittedPlace = usagePlace.text;
    final submittedItem = usageItem.text;
    final submittedAmount = amount.text;
    final parsedDueDay = int.tryParse(submittedDueDay.trim());
    final parsedAmount =
        int.tryParse(submittedAmount.replaceAll(',', '').trim());
    if (parsedDueDay == null ||
        parsedDueDay < 1 ||
        parsedDueDay > 31 ||
        submittedPlace.trim().isEmpty ||
        parsedAmount == null ||
        parsedAmount < 0) {
      return;
    }
    setState(() => _submitInFlight = true);
    try {
      final saved = await widget.state.createPlannedEntry(
        dueDay: parsedDueDay,
        usagePlace: submittedPlace,
        usageItem: submittedItem,
        amount: parsedAmount,
      );
      if (mounted &&
          saved &&
          dueDay.text == submittedDueDay &&
          usagePlace.text == submittedPlace &&
          usageItem.text == submittedItem &&
          amount.text == submittedAmount) {
        dueDay.clear();
        usagePlace.clear();
        usageItem.clear();
        amount.clear();
      }
    } finally {
      if (mounted) setState(() => _submitInFlight = false);
    }
  }
}

class _PlannedEntryItem extends StatefulWidget {
  const _PlannedEntryItem({
    required this.entry,
    required this.state,
    super.key,
  });

  final LedgerEntry entry;
  final AppState state;

  @override
  State<_PlannedEntryItem> createState() => _PlannedEntryItemState();
}

class _PlannedEntryItemState extends State<_PlannedEntryItem> {
  late String entryDate;
  late final TextEditingController actualAmount;
  late PlannedChargePreview preview;
  bool _confirmInFlight = false;

  @override
  void initState() {
    super.initState();
    entryDate = _plannedEntryDefaultDate(
        widget.state.currentMonth, widget.entry.dueDay);
    actualAmount =
        TextEditingController(text: (widget.entry.amountValue ?? 0).toString());
    preview = PlannedChargePreview(
      amountValue: widget.entry.amountValue ?? 0,
      discountPolicy: widget.entry.discountPolicy,
      automaticDiscountEligible: widget.entry.automaticDiscountEligible,
      effectiveDiscountAmount: widget.entry.effectiveDiscountAmount,
      effectiveAmountValue:
          widget.entry.effectiveAmountValue ?? widget.entry.amountValue ?? 0,
    );
  }

  @override
  void dispose() {
    actualAmount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final entry = widget.entry;
    final state = widget.state;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${entry.dueDay ?? '-'}일 ${entry.usagePlace ?? entry.title}',
                style:
                    const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
            if ((entry.usageItem ?? '').isNotEmpty)
              Text(entry.usageItem!, style: const TextStyle(color: moneyMuted)),
            const SizedBox(height: 8),
            _Line(label: '예정액', value: won(entry.amountValue)),
            const SizedBox(height: 8),
            TextField(
              key: ValueKey('planned-recurring-amount-${entry.id}'),
              controller: actualAmount,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: '실제 원금'),
              onEditingComplete: _refreshPreview,
            ),
            const SizedBox(height: 8),
            _Line(label: state.isOffline ? '할인(추정 불가)' : '할인', value: won(preview.effectiveDiscountAmount)),
            const SizedBox(height: 4),
            _Line(label: state.isOffline ? '실결제 예상액(할인 미반영)' : '실결제 예상액', value: won(preview.effectiveAmountValue)),
            const SizedBox(height: 8),
            DatePickerRow(
              label: '이번 승인 날짜',
              value: entryDate,
              onChanged: (value) => setState(() => entryDate = value),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed:
                        state.canConfirmCardRecurring && !_confirmInFlight
                            ? () => _confirm(context)
                            : null,
                    child: const Text('확인 처리'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: !state.canUseOnlineWrites
                        ? null
                        : () => state.deletePlannedEntry(entry.id),
                    style: OutlinedButton.styleFrom(foregroundColor: moneyRed),
                    child: const Text('삭제'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _refreshPreview() async {
    final parsedAmount =
        int.tryParse(actualAmount.text.replaceAll(',', '').trim());
    if (parsedAmount == null || parsedAmount < 0) return;
    try {
      final result =
          await widget.state.previewPlannedEntry(widget.entry.id, parsedAmount);
      if (mounted) setState(() => preview = result);
    } catch (_) {
      // 확인 단계에서 다시 조회하고 오류를 표시하므로 편집 중 네트워크 실패는 기존 값을 유지한다.
    }
  }

  Future<void> _confirm(BuildContext context) async {
    if (_confirmInFlight) return;
    final submittedAmount = actualAmount.text;
    final submittedDate = entryDate;
    final parsedAmount =
        int.tryParse(submittedAmount.replaceAll(',', '').trim());
    if (parsedAmount == null || parsedAmount < 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('실제 원금은 0원 이상의 정수로 입력하세요.')),
      );
      return;
    }
    setState(() => _confirmInFlight = true);
    late final PlannedChargePreview result;
    try {
      result =
          await widget.state.previewPlannedEntry(widget.entry.id, parsedAmount);
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('실결제 예상액을 확인하지 못했습니다: $error')),
        );
      }
      if (mounted) setState(() => _confirmInFlight = false);
      return;
    }
    if (!context.mounted) return;
    if (actualAmount.text != submittedAmount || entryDate != submittedDate) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('입력이 변경되었습니다. 현재 값으로 다시 확인하세요.')),
      );
      setState(() => _confirmInFlight = false);
      return;
    }
    setState(() => preview = result);
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('카드 정기결제 확인'),
        content: Text(
          '${widget.entry.usagePlace ?? widget.entry.title}을 $submittedDate 카드 지출로 반영할까요?\n\n'
          '예정 원금 ${won(widget.entry.amountValue)}\n'
          '실제 원금 ${won(result.amountValue)}\n'
          '할인 ${won(result.effectiveDiscountAmount)}\n'
          '실결제 예상액 ${won(result.effectiveAmountValue)}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('확인 처리'),
          ),
        ],
      ),
    );
    if (accepted == true) {
      await widget.state
          .confirmPlannedEntry(widget.entry.id, submittedDate, parsedAmount);
    }
    if (mounted) setState(() => _confirmInFlight = false);
  }
}

class _ConfirmedPlannedEntryItem extends StatelessWidget {
  const _ConfirmedPlannedEntryItem({required this.entry});

  final LedgerEntry entry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        color: moneyGreenSoft,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (entry.isOfflinePending)
              const Text('오프라인 보관 중',
                  style: TextStyle(color: moneyMuted)),
            Text('${entry.dueDay ?? '-'}일 ${entry.usagePlace ?? entry.title}',
                style:
                    const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
            if ((entry.usageItem ?? '').isNotEmpty)
              Text(entry.usageItem!, style: const TextStyle(color: moneyMuted)),
            const SizedBox(height: 8),
            _Line(label: '예정 원금', value: won(entry.amountValue)),
            const SizedBox(height: 4),
            _Line(
                label: '실제 원금',
                value: won(entry.confirmedAmountValue ?? entry.amountValue)),
            const SizedBox(height: 4),
            _Line(
                label: '할인',
                value: won(entry.confirmedEffectiveDiscountAmount ?? 0)),
            const SizedBox(height: 4),
            _Line(
                label: '실결제액',
                value: won(entry.confirmedEffectiveAmountValue ??
                    entry.confirmedAmountValue ??
                    entry.amountValue)),
            const SizedBox(height: 4),
            const Text('이번 달 원장에 편입되었습니다.',
                style:
                    TextStyle(color: moneyMuted, fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }
}

String _plannedEntryDefaultDate(String month, int? dueDay) {
  final parts = month.split('-');
  if (parts.length != 2) {
    return DateTime.now().toIso8601String().substring(0, 10);
  }
  final year = int.tryParse(parts[0]);
  final monthValue = int.tryParse(parts[1]);
  if (year == null || monthValue == null) {
    return DateTime.now().toIso8601String().substring(0, 10);
  }
  final lastDay = DateTime(year, monthValue + 1, 0).day;
  final day = (dueDay ?? 1).clamp(1, lastDay);
  return '${year.toString().padLeft(4, '0')}-${monthValue.toString().padLeft(2, '0')}-${day.toString().padLeft(2, '0')}';
}
