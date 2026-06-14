import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class FamilyScreen extends StatefulWidget {
  const FamilyScreen({required this.state, super.key});

  final AppState state;

  @override
  State<FamilyScreen> createState() => _FamilyScreenState();
}

class _FamilyScreenState extends State<FamilyScreen> {
  String panelType = 'claim';
  final title = TextEditingController();
  final amount = TextEditingController();
  bool? discountEnabled;

  @override
  void dispose() {
    title.dispose();
    amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final rows = widget.state.panelsByType(panelType);
    final isClaim = panelType == 'claim';
    final discountValue = discountEnabled ?? _defaultDiscountEnabled();
    final discountPolicyEnabled = _defaultDiscountEnabled();
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        const Text('가족',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
        const SizedBox(height: 14),
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: 'claim', label: Text('청구')),
            ButtonSegment(value: 'family_card', label: Text('가족카드')),
          ],
          selected: {panelType},
          onSelectionChanged: (value) => setState(() {
            panelType = value.first;
            discountEnabled = null;
          }),
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
                child: AmountTile(
                    label: '원금 합계',
                    amount: won(widget.state.panelOriginalTotal(panelType)))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(
                    label: isClaim ? '실청구 합계' : '실결제 합계',
                    amount: won(_effectiveTotal(rows, discountPolicyEnabled)))),
          ],
        ),
        const SectionTitle('추가'),
        MoneyCard(
          child: Column(
            children: [
              TextField(
                  controller: title,
                  decoration: InputDecoration(
                      labelText: isClaim ? '청구 내용' : '가족카드 내용')),
              const SizedBox(height: 12),
              TextField(
                controller: amount,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: '금액'),
                onSubmitted: (_) => _submit(),
              ),
              const SizedBox(height: 8),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('할인 적용'),
                subtitle: const Text('체크를 끄면 이 항목은 할인 제외로 등록합니다.'),
                value: discountValue,
                onChanged: (value) =>
                    setState(() => discountEnabled = value ?? false),
              ),
              const SizedBox(height: 14),
              ElevatedButton(
                  onPressed: widget.state.isBusy ? null : _submit,
                  child: Text(isClaim ? '청구 추가' : '가족카드 추가')),
            ],
          ),
        ),
        const SectionTitle('목록'),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: widget.state.isBusy
                    ? null
                    : () => widget.state.sharePanel(panelType),
                child: const Text('공유하기'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: ElevatedButton(
                onPressed: widget.state.isBusy || rows.isEmpty
                    ? null
                    : () => widget.state.completePanelType(panelType),
                child: const Text('일괄 처리 완료'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (rows.isEmpty)
          MoneyCard(
            child: Text(isClaim ? '청구 내역이 없습니다.' : '가족카드 내역이 없습니다.'),
          ),
        ...rows.map((panel) => _FamilyItem(
              panel: panel,
              state: widget.state,
              isClaim: isClaim,
              discountPolicyEnabled: discountPolicyEnabled,
            )),
      ],
    );
  }

  Future<void> _submit() async {
    final parsedAmount = int.tryParse(amount.text.replaceAll(',', '').trim());
    if (title.text.trim().isEmpty || parsedAmount == null || parsedAmount < 0) {
      return;
    }
    await widget.state.createPanel(
      panelType: panelType,
      title: title.text,
      amount: parsedAmount,
      discountEnabled: discountEnabled ?? _defaultDiscountEnabled(),
    );
    title.clear();
    amount.clear();
    discountEnabled = null;
  }

  bool _defaultDiscountEnabled() {
    if (panelType == 'family_card') {
      return widget.state.familyDiscountMonth?.isEnabled ?? false;
    }
    return widget.state.ownerDiscountMonth?.isEnabled ?? true;
  }

  int _effectiveTotal(List<MonthlyPanel> rows, bool discountPolicyEnabled) {
    return rows.fold(
        0,
        (sum, panel) =>
            sum + panel.effectiveAmountForPolicy(discountPolicyEnabled));
  }
}

class _FamilyItem extends StatelessWidget {
  const _FamilyItem(
      {required this.panel,
      required this.state,
      required this.isClaim,
      required this.discountPolicyEnabled});

  final MonthlyPanel panel;
  final AppState state;
  final bool isClaim;
  final bool discountPolicyEnabled;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${shortDate(panel.spentOn)} ${panel.title}'.trim(),
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 12),
            _Line(label: '원금', value: won(panel.amountValue)),
            _Line(
                label: '할인',
                value: won(panel.discountForPolicy(discountPolicyEnabled))),
            _Line(
                label: isClaim ? '실청구' : '실결제',
                value:
                    won(panel.effectiveAmountForPolicy(discountPolicyEnabled))),
            const SizedBox(height: 10),
            Row(
              children: [
                if (discountPolicyEnabled) ...[
                  Expanded(
                    child: OutlinedButton(
                      onPressed: state.isBusy ? null : _toggleDiscount,
                      child: Text(panel.isDiscountExcluded ? '할인 적용' : '할인 제외'),
                    ),
                  ),
                  const SizedBox(width: 10),
                ],
                Expanded(
                  child: OutlinedButton(
                    onPressed:
                        state.isBusy ? null : () => state.deletePanel(panel.id),
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

  Future<void> _toggleDiscount() async {
    if (panel.isDiscountExcluded) {
      await state.applyDefaultPanelDiscount(panel.id);
    } else {
      await state.excludeExistingPanelDiscount(panel.id);
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
