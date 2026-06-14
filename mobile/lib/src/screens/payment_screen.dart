import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class PaymentScreen extends StatefulWidget {
  const PaymentScreen({required this.state, super.key});

  final AppState state;

  @override
  State<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends State<PaymentScreen> {
  final autoAmount = TextEditingController();

  @override
  void dispose() {
    autoAmount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final status = widget.state.cardPayments;
    final rows = status?.rows ?? [];
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        const Text('이번달 결제',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
              color: moneyGreen, borderRadius: BorderRadius.circular(22)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('남은 결제액',
                  style: TextStyle(
                      color: moneyGreenSoft, fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              Text(won(status?.effectiveRemainingTotal),
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 34,
                      fontWeight: FontWeight.w900)),
              const SizedBox(height: 6),
              Text(_dueText(status?.dueDate),
                  style: const TextStyle(color: Colors.white)),
            ],
          ),
        ),
        const SectionTitle('자동 배분'),
        MoneyCard(
          child: Column(
            children: [
              TextField(
                controller: autoAmount,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: '처리 가능액 입력'),
              ),
              const SizedBox(height: 12),
              const OutlinedButton(onPressed: null, child: Text('날짜순 자동 배분')),
            ],
          ),
        ),
        SectionTitle('결제 항목',
            trailing: Text('${rows.length}건',
                style: const TextStyle(color: moneyMuted))),
        if (rows.isEmpty) const MoneyCard(child: Text('결제 대상 사용내역이 없습니다.')),
        ...rows.map((row) => _PaymentItemCard(row: row, state: widget.state)),
      ],
    );
  }

  String _dueText(String? dueDate) {
    if (dueDate == null || dueDate.isEmpty) return '결제일 정보 없음';
    final due = DateTime.tryParse(dueDate);
    if (due == null) return '결제일 $dueDate';
    final days = due.difference(DateTime.now()).inDays + 1;
    return days >= 0 ? '결제일까지 $days일 남음' : '결제일이 지났습니다';
  }
}

class _PaymentItemCard extends StatelessWidget {
  const _PaymentItemCard({required this.row, required this.state});

  final CardPaymentRow row;
  final AppState state;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(row.title,
                style:
                    const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
            const SizedBox(height: 12),
            _Line(label: '원금', value: won(row.originalAmount)),
            _Line(label: '즉시결제', value: won(row.immediatePaidAmount)),
            _Line(label: '할인', value: won(row.discountAmount)),
            _Line(label: '남은 금액', value: won(row.remainingAmount)),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: state.isBusy || row.remainingAmount <= 0
                        ? null
                        : () => state.payImmediately(row),
                    child: const Text('즉시결제'),
                  ),
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: OutlinedButton(onPressed: null, child: Text('이월')),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Line extends StatelessWidget {
  const _Line({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
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
