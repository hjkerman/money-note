import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class CashFlowScreen extends StatefulWidget {
  const CashFlowScreen({required this.state, super.key});

  final AppState state;

  @override
  State<CashFlowScreen> createState() => _CashFlowScreenState();
}

class _CashFlowScreenState extends State<CashFlowScreen> {
  final title = TextEditingController();
  final amount = TextEditingController();
  bool isIncome = true;
  bool isPrimaryIncome = false;
  late String selectedDate;
  bool _submitInFlight = false;

  @override
  void initState() {
    super.initState();
    selectedDate = widget.state.serverToday;
  }

  @override
  void dispose() {
    title.dispose();
    amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final flows = [...widget.state.cashFlows]..sort((a, b) {
        final dateCompare = b.occurredOn.compareTo(a.occurredOn);
        if (dateCompare != 0) return dateCompare;
        return b.id.compareTo(a.id);
      });
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        const Text('현금흐름',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
                child: AmountTile(
                    label: widget.state.financialValuesAreEstimated
                        ? '현금흐름 반영액(예상)'
                        : '현금흐름 반영액',
                    amount: won(widget.state.summary?.cashFlowBalance))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(
                    label: widget.state.financialValuesAreEstimated
                        ? '잔여 유동성(예상)'
                        : '잔여 유동성',
                    amount: won(widget.state.summary?.remainingLiquidity))),
          ],
        ),
        const SectionTitle('현금 입출금 입력'),
        MoneyCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(value: true, label: Text('입금')),
                  ButtonSegment(value: false, label: Text('출금')),
                ],
                selected: {isIncome},
                onSelectionChanged: (value) => setState(() {
                  isIncome = value.first;
                  if (!isIncome) isPrimaryIncome = false;
                }),
              ),
              const SizedBox(height: 12),
              _DatePickerRow(
                label: '일자',
                value: selectedDate,
                onChanged: (value) => setState(() => selectedDate = value),
              ),
              const SizedBox(height: 12),
              TextField(
                  controller: title,
                  decoration: const InputDecoration(labelText: '내용')),
              const SizedBox(height: 12),
              TextField(
                controller: amount,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: '금액'),
                onSubmitted: (_) => _submit(),
              ),
              if (isIncome) ...[
                const SizedBox(height: 8),
                Material(
                  color: Colors.transparent,
                  child: CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('이달 기준 수입'),
                    subtitle: const Text('예산심사위원회의 이번 달 기준 수입으로 봅니다.'),
                    value: isPrimaryIncome,
                    onChanged: (value) =>
                        setState(() => isPrimaryIncome = value ?? false),
                  ),
                ),
              ],
              const SizedBox(height: 12),
              ElevatedButton(
                  onPressed: widget.state.canCreateCashFlow && !_submitInFlight
                      ? _submit
                      : null,
                  child: const Text('현금흐름 추가')),
            ],
          ),
        ),
        SectionTitle('최근 현금흐름',
            trailing: Text('${flows.length}건',
                style: const TextStyle(color: moneyMuted))),
        if (flows.isEmpty) const MoneyCard(child: Text('현금흐름 기록이 없습니다.')),
        ...flows.map((flow) => _CashFlowCard(flow: flow, state: widget.state)),
      ],
    );
  }

  Future<void> _submit() async {
    if (_submitInFlight) return;
    final submittedTitle = title.text;
    final submittedAmount = amount.text;
    final submittedDate = selectedDate;
    final submittedIsIncome = isIncome;
    final submittedIsPrimaryIncome = isPrimaryIncome;
    final parsedAmount =
        int.tryParse(submittedAmount.replaceAll(',', '').trim());
    if (submittedTitle.trim().isEmpty ||
        parsedAmount == null ||
        parsedAmount < 0) {
      return;
    }
    setState(() => _submitInFlight = true);
    final saved = await widget.state.createCashFlow(
      occurredOn: submittedDate,
      title: submittedTitle,
      amount: parsedAmount,
      isIncome: submittedIsIncome,
      isPrimaryIncome: submittedIsPrimaryIncome,
    );
    if (!mounted) return;
    final draftIsUnchanged = title.text == submittedTitle &&
        amount.text == submittedAmount &&
        selectedDate == submittedDate &&
        isIncome == submittedIsIncome &&
        isPrimaryIncome == submittedIsPrimaryIncome;
    if (saved && draftIsUnchanged) {
      title.clear();
      amount.clear();
      setState(() {
        _submitInFlight = false;
        isPrimaryIncome = false;
        selectedDate = widget.state.serverToday;
      });
      return;
    }
    setState(() => _submitInFlight = false);
  }
}

class _DatePickerRow extends StatelessWidget {
  const _DatePickerRow({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: () async {
        final initialDate = DateTime.tryParse(value) ?? DateTime.now();
        final picked = await showDatePicker(
          context: context,
          initialDate: initialDate,
          firstDate: DateTime(2020, 1, 1),
          lastDate: DateTime(2100, 12, 31),
        );
        if (picked == null) return;
        onChanged(
            '${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}');
      },
      child: Row(
        children: [
          Text(label),
          const Spacer(),
          Text(shortDate(value),
              style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _CashFlowCard extends StatelessWidget {
  const _CashFlowCard({required this.flow, required this.state});

  final CashFlow flow;
  final AppState state;

  @override
  Widget build(BuildContext context) {
    final isIncome = flow.amountValue >= 0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Row(
          children: [
            SizedBox(
              width: 54,
              child: Text(shortDate(flow.occurredOn),
                  style: const TextStyle(
                      color: moneyGreen, fontWeight: FontWeight.w800)),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(flow.title,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w900)),
                  if (flow.isOfflinePending)
                    const Text('오프라인 보관 중',
                        style: TextStyle(color: moneyMuted)),
                  if (flow.isPrimaryIncome)
                    const Text('이달 기준 수입', style: TextStyle(color: moneyMuted)),
                ],
              ),
            ),
            Text(
              '${isIncome ? '+' : '-'}${won(flow.amountValue.abs())}',
              style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w900,
                  color: isIncome ? moneyGreen : moneyRed),
            ),
            IconButton(
              onPressed: state.canUseOnlineWrites
                  ? () => state.deleteCashFlow(flow.id)
                  : null,
              icon: const Icon(Icons.delete_outline),
              tooltip: '삭제',
            ),
          ],
        ),
      ),
    );
  }
}
