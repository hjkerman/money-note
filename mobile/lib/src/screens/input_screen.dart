import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'notification_import_screen.dart';

class InputScreen extends StatefulWidget {
  const InputScreen({required this.state, super.key});

  final AppState state;

  @override
  State<InputScreen> createState() => _InputScreenState();
}

class _InputScreenState extends State<InputScreen> {
  final place = TextEditingController();
  final item = TextEditingController();
  final amount = TextEditingController();
  final placeFocus = FocusNode();

  @override
  void dispose() {
    place.dispose();
    item.dispose();
    amount.dispose();
    placeFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final summary = widget.state.summary;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        Text('${widget.state.currentMonth.replaceFirst('-', '년 ')}월',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
                child:
                    AmountTile(label: '카드대금', amount: won(summary?.cardTotal))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(
                    label: '익월 유동성', amount: won(summary?.nextMonthLiquidity))),
          ],
        ),
        const SectionTitle('오늘 지출 입력'),
        MoneyCard(
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: place,
                      focusNode: placeFocus,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(labelText: '사용처'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    width: 118,
                    child: TextField(
                      controller: amount,
                      keyboardType: TextInputType.number,
                      textInputAction: TextInputAction.done,
                      decoration: const InputDecoration(labelText: '금액'),
                      onSubmitted: (_) => _submit(),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: item,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(labelText: '사용항목'),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                  onPressed: widget.state.isBusy ? null : _submit,
                  child: const Text('지출 추가')),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                      builder: (_) => const NotificationImportScreen()),
                ),
                child: const Text('알림에서 가져오기'),
              ),
            ],
          ),
        ),
        const SectionTitle('최근 입력',
            trailing: Text('최근 5건', style: TextStyle(color: moneyMuted))),
        ...widget.state.recentEntries.map(_RecentEntryCard.new),
        if (widget.state.statusMessage.isNotEmpty)
          _StatusMessage(widget.state.statusMessage),
      ],
    );
  }

  Future<void> _submit() async {
    final parsedAmount = int.tryParse(amount.text.replaceAll(',', '').trim());
    if (place.text.trim().isEmpty || parsedAmount == null || parsedAmount < 0) {
      return;
    }
    await widget.state.createExpense(
      usagePlace: place.text,
      usageItem: item.text,
      amount: parsedAmount,
    );
    place.clear();
    item.clear();
    amount.clear();
    placeFocus.requestFocus();
  }
}

class _RecentEntryCard extends StatelessWidget {
  const _RecentEntryCard(this.entry);

  final LedgerEntry entry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        padding: const EdgeInsets.all(14),
        child: Row(
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
                          fontSize: 16, fontWeight: FontWeight.w800)),
                  if ((entry.usageItem ?? '').isNotEmpty)
                    Text(entry.usageItem!,
                        style: const TextStyle(color: moneyMuted)),
                ],
              ),
            ),
            Text(won(entry.amountValue),
                style:
                    const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
          ],
        ),
      ),
    );
  }
}

class _StatusMessage extends StatelessWidget {
  const _StatusMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Text(message, style: const TextStyle(color: moneyMuted)),
    );
  }
}
