part of 'management_screen.dart';

class PanelManagementScreen extends StatefulWidget {
  const PanelManagementScreen({
    required this.state,
    required this.panelType,
    required this.title,
    required this.inputLabel,
    required this.emptyText,
    super.key,
  });

  final AppState state;
  final String panelType;
  final String title;
  final String inputLabel;
  final String emptyText;

  @override
  State<PanelManagementScreen> createState() => _PanelManagementScreenState();
}

class _PanelManagementScreenState extends State<PanelManagementScreen> {
  final title = TextEditingController();
  final amount = TextEditingController();
  bool _submitInFlight = false;

  @override
  void dispose() {
    title.dispose();
    amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.state,
      builder: (context, _) {
        final rows = widget.state.panelsByType(widget.panelType);
        final activeRows = widget.panelType == 'fixed'
            ? rows
                .where((panel) =>
                    panel.confirmedAt == null ||
                    panel.confirmedCashFlowId == null)
                .toList()
            : rows;
        final confirmedRows = widget.panelType == 'fixed'
            ? rows
                .where((panel) =>
                    panel.confirmedAt != null &&
                    panel.confirmedCashFlowId != null)
                .toList()
            : <MonthlyPanel>[];
        final summary = widget.state.summary;
        return Scaffold(
          appBar: AppBar(title: Text(widget.title)),
          body: RefreshIndicator(
            onRefresh: widget.state.refreshPanelManagementArea,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
              children: [
                AmountTile(
                  label: widget.panelType == 'fixed'
                      ? widget.state.financialValuesAreEstimated
                          ? '처리액 / 전체 고정지출액(예상)'
                          : '처리액 / 전체 고정지출액'
                      : '합계',
                  amount: widget.panelType == 'fixed'
                      ? '${won(summary?.fixedCashProcessedTotal)} / 총 ${won(summary?.fixedCashTotal)}'
                      : won(rows.fold<int>(
                          0, (sum, panel) => sum + (panel.amountValue ?? 0))),
                ),
                const SectionTitle('등록'),
                MoneyCard(
                  child: Column(
                    children: [
                      TextField(
                          controller: title,
                          decoration:
                              InputDecoration(labelText: widget.inputLabel)),
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
                          child: const Text('추가')),
                    ],
                  ),
                ),
                SectionTitle('목록',
                    trailing: Text('${activeRows.length}건',
                        style: const TextStyle(color: moneyMuted))),
                if (activeRows.isEmpty)
                  MoneyCard(child: Text(widget.emptyText)),
                ...activeRows.map((panel) => widget.panelType == 'fixed'
                    ? _FixedPanelManagementItem(
                        key: ValueKey('fixed-recurring-${panel.id}'),
                        panel: panel,
                        state: widget.state,
                      )
                    : _PanelManagementItem(
                        panel: panel,
                        state: widget.state,
                      )),
                if (widget.panelType == 'fixed' &&
                    confirmedRows.isNotEmpty) ...[
                  SectionTitle(
                    '이번 달 처리된 현금성 고정지출',
                    trailing: Text('${confirmedRows.length}건',
                        style: const TextStyle(color: moneyMuted)),
                  ),
                  ...confirmedRows.map((panel) => _ConfirmedFixedPanelItem(
                        panel: panel,
                        state: widget.state,
                      )),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _submit() async {
    if (_submitInFlight) return;
    final submittedTitle = title.text;
    final submittedAmount = amount.text;
    final parsedAmount =
        int.tryParse(submittedAmount.replaceAll(',', '').trim());
    if (submittedTitle.trim().isEmpty ||
        parsedAmount == null ||
        parsedAmount < 0) {
      return;
    }
    setState(() => _submitInFlight = true);
    try {
      final saved = await widget.state.createPanel(
        panelType: widget.panelType,
        title: submittedTitle,
        amount: parsedAmount,
        discountEnabled: true,
      );
      if (mounted &&
          saved &&
          title.text == submittedTitle &&
          amount.text == submittedAmount) {
        title.clear();
        amount.clear();
      }
    } finally {
      if (mounted) setState(() => _submitInFlight = false);
    }
  }
}

class _PanelManagementItem extends StatelessWidget {
  const _PanelManagementItem({required this.panel, required this.state});

  final MonthlyPanel panel;
  final AppState state;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (panel.panelType == 'frozen')
                    Text('등록일자 ${_registrationDateLabel(panel.spentOn)}',
                        style: const TextStyle(
                            color: moneyMuted,
                            fontSize: 12,
                            fontWeight: FontWeight.w700)),
                  Text(panel.title,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w900)),
                ],
              ),
            ),
            Text(won(panel.amountValue),
                style: const TextStyle(fontWeight: FontWeight.w900)),
            IconButton(
              onPressed: state.canUseOnlineWrites
                  ? () => state.deletePanel(panel.id)
                  : null,
              icon: const Icon(Icons.delete_outline),
              tooltip: '삭제',
            ),
          ],
        ),
      ),
    );
  }

  String _registrationDateLabel(String? value) {
    final label = shortDate(value);
    return label.isEmpty ? '미상' : label;
  }
}

class _FixedPanelManagementItem extends StatefulWidget {
  const _FixedPanelManagementItem({
    required this.panel,
    required this.state,
    super.key,
  });

  final MonthlyPanel panel;
  final AppState state;

  @override
  State<_FixedPanelManagementItem> createState() =>
      _FixedPanelManagementItemState();
}

class _FixedPanelManagementItemState extends State<_FixedPanelManagementItem> {
  late String occurredOn;
  late final TextEditingController actualAmount;
  bool _confirmInFlight = false;

  @override
  void initState() {
    super.initState();
    occurredOn = widget.state.serverToday;
    actualAmount =
        TextEditingController(text: (widget.panel.amountValue ?? 0).toString());
  }

  @override
  void dispose() {
    actualAmount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final panel = widget.panel;
    final state = widget.state;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(panel.title,
                style:
                    const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            _Line(label: '예정액', value: won(panel.amountValue)),
            const SizedBox(height: 8),
            TextField(
              key: ValueKey('fixed-recurring-amount-${panel.id}'),
              controller: actualAmount,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: '실제 출금액'),
            ),
            const SizedBox(height: 8),
            DatePickerRow(
              label: '처리일',
              value: occurredOn,
              onChanged: (value) => setState(() => occurredOn = value),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: state.canConfirmRecurring && !_confirmInFlight
                        ? () => _confirm(context)
                        : null,
                    child: const Text('확인 처리'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: state.canUseOnlineWrites
                        ? () => state.deletePanel(panel.id)
                        : null,
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

  Future<void> _confirm(BuildContext context) async {
    if (_confirmInFlight) return;
    final submittedAmount = actualAmount.text;
    final submittedDate = occurredOn;
    final parsedAmount =
        int.tryParse(submittedAmount.replaceAll(',', '').trim());
    if (parsedAmount == null || parsedAmount < 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('실제 출금액은 0원 이상의 정수로 입력하세요.')),
      );
      return;
    }
    setState(() => _confirmInFlight = true);
    try {
      final accepted = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('현금성 고정지출 확인'),
          content: Text(
            '${widget.panel.title}을 $submittedDate 현금 지출로 반영할까요?\n\n'
            '예정액 ${won(widget.panel.amountValue)}\n'
            '실제 출금액 ${won(parsedAmount)}',
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
            .confirmFixedPanel(widget.panel.id, submittedDate, parsedAmount);
      }
    } finally {
      if (mounted) setState(() => _confirmInFlight = false);
    }
  }
}

class _ConfirmedFixedPanelItem extends StatelessWidget {
  const _ConfirmedFixedPanelItem({required this.panel, required this.state});

  final MonthlyPanel panel;
  final AppState state;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (panel.isOfflinePending)
              const Text('오프라인 보관 중', style: TextStyle(color: moneyMuted)),
            Text('처리일 ${shortDate(panel.spentOn)}',
                style: const TextStyle(
                    color: moneyMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text(panel.title,
                style:
                    const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            _Line(label: '예정액', value: won(panel.amountValue)),
            const SizedBox(height: 4),
            _Line(
                label: '실제 출금액',
                value: won(panel.confirmedAmountValue ?? panel.amountValue)),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: !state.canUseOnlineWrites ||
                            panel.confirmedCashFlowId == null
                        ? null
                        : () => state.cancelFixedPanelConfirmation(
                            panel.confirmedCashFlowId!),
                    child: const Text('확인 취소'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: state.canUseOnlineWrites
                        ? () => state.deletePanel(panel.id)
                        : null,
                    style: OutlinedButton.styleFrom(foregroundColor: moneyRed),
                    child: const Text('정기지출 해제'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
