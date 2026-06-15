import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class MonthEntriesScreen extends StatelessWidget {
  const MonthEntriesScreen({required this.state, super.key});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final rows = state.expenseEntries;
    final discountPolicyEnabled = state.ownerDiscountMonth?.isEnabled ?? true;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        Text('${state.currentMonth.replaceFirst('-', '년 ')}월 내역',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
        const SizedBox(height: 14),
        AmountTile(
            label: '월 지출',
            amount: won(rows.fold<int>(
                0, (sum, entry) => sum + (entry.amountValue ?? 0)))),
        SectionTitle('전체 지출',
            trailing: Text('${rows.length}건',
                style: const TextStyle(color: moneyMuted))),
        if (rows.isEmpty) const MoneyCard(child: Text('이번 달 지출 내역이 없습니다.')),
        ...rows.map((entry) => _MonthEntryCard(
              entry: entry,
              state: state,
              discountPolicyEnabled: discountPolicyEnabled,
            )),
      ],
    );
  }
}

class _MonthEntryCard extends StatelessWidget {
  const _MonthEntryCard({
    required this.entry,
    required this.state,
    required this.discountPolicyEnabled,
  });

  final LedgerEntry entry;
  final AppState state;
  final bool discountPolicyEnabled;

  @override
  Widget build(BuildContext context) {
    final discount = entry.discountForPolicy(discountPolicyEnabled);
    final canToggleDiscount = discountPolicyEnabled &&
        entry.paymentKey != null &&
        entry.paymentKey!.isNotEmpty;
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
                    if (discountPolicyEnabled && entry.paymentKey != null) ...[
                      const SizedBox(height: 3),
                      Text('할인 ${won(discount)}',
                          style: const TextStyle(
                              color: moneyGreen,
                              fontSize: 12,
                              fontWeight: FontWeight.w800)),
                      Text('실결제 ${won(entry.effectiveAmountForPolicy(true))}',
                          style: const TextStyle(
                              color: moneyMuted,
                              fontSize: 12,
                              fontWeight: FontWeight.w700)),
                    ],
                  ],
                ),
              ],
            ),
            if (canToggleDiscount) ...[
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: state.isBusy ? null : _toggleDiscount,
                child: Text(entry.isDiscountExcluded ? '할인 적용' : '할인 제외'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _toggleDiscount() async {
    final paymentKey = entry.paymentKey;
    if (paymentKey == null || paymentKey.isEmpty) return;
    if (entry.isDiscountExcluded) {
      await state.applyDefaultEntryDiscount(paymentKey);
    } else {
      await state.excludeExistingEntryDiscount(paymentKey);
    }
  }

  bool _isTransport(LedgerEntry entry) => _title(entry).contains('교통');

  bool _isToll(LedgerEntry entry) {
    final title = _title(entry);
    return title.contains('통행') || title.contains('하이패스');
  }

  String _title(LedgerEntry entry) {
    return '${entry.title} ${entry.usagePlace ?? ''} ${entry.usageItem ?? ''}';
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
