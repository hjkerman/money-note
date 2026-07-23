import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'input_screen.dart';

class MonthEntriesScreen extends StatelessWidget {
  const MonthEntriesScreen({required this.state, super.key});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final rows = state.expenseEntries;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        Text('${state.currentMonth.replaceFirst('-', '년 ')}월 내역',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
        const SizedBox(height: 14),
        AmountTile(
            label: '월 지출', amount: won(state.summary?.currentSpendingTotal)),
        const SectionTitle('카드 지출 입력'),
        ExpenseInputCard(state: state),
        SectionTitle('전체 지출',
            trailing: Text('${rows.length}건',
                style: const TextStyle(color: moneyMuted))),
        if (rows.isEmpty) const MoneyCard(child: Text('이번 달 지출 내역이 없습니다.')),
        ...rows.map((entry) => _MonthEntryCard(
              entry: entry,
              state: state,
            )),
      ],
    );
  }
}

class _MonthEntryCard extends StatelessWidget {
  const _MonthEntryCard({
    required this.entry,
    required this.state,
  });

  final LedgerEntry entry;
  final AppState state;

  @override
  Widget build(BuildContext context) {
    final discountEligible = !entry.isDiscountIneligible;
    final discount = entry.effectiveDiscountAmount;
    final canToggleDiscount = entry.isDiscountPolicyEnabled &&
        discountEligible &&
        entry.paymentKey != null &&
        entry.paymentKey!.isNotEmpty;
    final canEditNetAmount = entry.paymentKey != null &&
        entry.paymentKey!.isNotEmpty &&
        entry.amountValue != null;
    final showDiscountInfo = canToggleDiscount || entry.discountOverride != 0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 54,
                  child: Text(shortDate(entry.entryDate),
                      style: const TextStyle(
                          color: moneyGreen, fontWeight: FontWeight.w800)),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(entry.usagePlace ?? entry.title,
                          style: const TextStyle(
                              fontSize: 16, fontWeight: FontWeight.w900)),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          if ((entry.usageItem ?? '').isNotEmpty)
                            Text(entry.usageItem!,
                                style: const TextStyle(color: moneyMuted)),
                          if (_isTransport(entry)) const _Badge('교통'),
                          if (_isToll(entry)) const _Badge('통행료'),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(won(entry.amountValue),
                        style: const TextStyle(
                            fontSize: 17, fontWeight: FontWeight.w900)),
                    if (showDiscountInfo) ...[
                      const SizedBox(height: 3),
                      Text('할인 ${won(discount)}',
                          style: const TextStyle(
                              color: moneyGreen,
                              fontSize: 12,
                              fontWeight: FontWeight.w800)),
                      Text('실결제 ${won(entry.effectiveAmount)}',
                          style: const TextStyle(
                              color: moneyMuted,
                              fontSize: 12,
                              fontWeight: FontWeight.w700)),
                    ],
                  ],
                ),
              ],
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: normalizeSpendingCategory(entry.spendingCategory),
              decoration: const InputDecoration(labelText: '분류'),
              items: spendingCategoryOptions
                  .map((option) => DropdownMenuItem<String>(
                        value: option.value,
                        child: Text(option.label),
                      ))
                  .toList(),
              onChanged: state.isBusy
                  ? null
                  : (value) => state.updateExpenseCategory(entry.id, value),
            ),
            const SizedBox(height: 10),
            if (canToggleDiscount || canEditNetAmount)
              Row(
                children: [
                  if (canToggleDiscount)
                    Expanded(
                      child: OutlinedButton(
                        onPressed: state.isBusy ? null : _toggleDiscount,
                        child:
                            Text(entry.isDiscountExcluded ? '할인 적용' : '할인 제외'),
                      ),
                    ),
                  if (canToggleDiscount && canEditNetAmount)
                    const SizedBox(width: 10),
                  if (canEditNetAmount)
                    Expanded(
                      child: OutlinedButton(
                        onPressed:
                            state.isBusy ? null : () => _editNetAmount(context),
                        child: const Text('실결제액 수정'),
                      ),
                    ),
                ],
              ),
            const SizedBox(height: 10),
            OutlinedButton(
              onPressed: state.isBusy ? null : () => _confirmDelete(context),
              style: OutlinedButton.styleFrom(foregroundColor: moneyRed),
              child: const Text('삭제'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _toggleDiscount() async {
    if (entry.isDiscountIneligible) return;
    final paymentKey = entry.paymentKey;
    if (paymentKey == null || paymentKey.isEmpty) return;
    if (entry.isDiscountExcluded) {
      await state.applyDefaultEntryDiscount(paymentKey);
    } else {
      await state.excludeExistingEntryDiscount(paymentKey);
    }
  }

  Future<void> _editNetAmount(BuildContext context) async {
    final amount = entry.amountValue;
    if (amount == null) return;
    final controller =
        TextEditingController(text: entry.effectiveAmount.toString());
    final netAmount = await showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('실결제액 수정'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          autofocus: true,
          decoration: const InputDecoration(labelText: '실결제액'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () {
              final parsed =
                  int.tryParse(controller.text.replaceAll(',', '').trim());
              if (parsed == null || parsed < 0 || parsed > amount) return;
              Navigator.of(context).pop(parsed);
            },
            child: const Text('저장'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (netAmount == null) return;
    await state.updateEntryNetAmount(entry, netAmount);
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('지출 삭제'),
        content: Text('${entry.usagePlace ?? entry.title} 항목을 삭제할까요?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('삭제'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await state.deleteExpense(entry.id);
    }
  }

  bool _isTransport(LedgerEntry entry) {
    return entry.isTransport;
  }

  bool _isToll(LedgerEntry entry) {
    return entry.isToll;
  }
}

class _Badge extends StatelessWidget {
  const _Badge(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: moneyGreenSoft,
        border: Border.all(color: const Color(0xFFB9C7AE)),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(text,
          style: const TextStyle(
              color: moneyGreen, fontSize: 11, fontWeight: FontWeight.w800)),
    );
  }
}
