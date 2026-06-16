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
  late String selectedDate;

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
    final rows = widget.state.panelsByType(panelType);
    final isClaim = panelType == 'claim';
    final discountValue = discountEnabled ?? _defaultDiscountEnabled();
    final discountPolicyEnabled = _defaultDiscountEnabled();
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        const Text('정산',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: _SettlementSwitchCard(
                title: '청구',
                subtitle: '집안 생활비 정산',
                amount: won(_effectiveTotal(widget.state.panelsByType('claim'),
                    widget.state.ownerDiscountMonth?.isEnabled ?? true)),
                selected: panelType == 'claim',
                onTap: () => _selectPanel('claim'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _SettlementSwitchCard(
                title: '가족카드',
                subtitle: '가족카드 사용액',
                amount: won(_effectiveTotal(
                    widget.state.panelsByType('family_card'),
                    widget.state.familyDiscountMonth?.isEnabled ?? false)),
                selected: panelType == 'family_card',
                onTap: () => _selectPanel('family_card'),
              ),
            ),
          ],
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
              _DatePickerRow(
                label: '사용 일자',
                value: selectedDate,
                onChanged: (value) => setState(() => selectedDate = value),
              ),
              const SizedBox(height: 12),
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
      spentOn: selectedDate,
    );
    title.clear();
    amount.clear();
    discountEnabled = null;
    setState(() => selectedDate = widget.state.serverToday);
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

  void _selectPanel(String nextPanelType) {
    setState(() {
      panelType = nextPanelType;
      discountEnabled = null;
      selectedDate = widget.state.serverToday;
    });
  }
}

class _SettlementSwitchCard extends StatelessWidget {
  const _SettlementSwitchCard({
    required this.title,
    required this.subtitle,
    required this.amount,
    required this.selected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final String amount;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return MoneyCard(
      color: selected ? moneyGreenSoft : Colors.white,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title,
                style:
                    const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
            const SizedBox(height: 4),
            Text(subtitle,
                style: const TextStyle(
                    color: moneyMuted, fontWeight: FontWeight.w600)),
            const SizedBox(height: 10),
            Text(amount,
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          ],
        ),
      ),
    );
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
    final discountEligible =
        discountPolicyEnabled && !panel.isDiscountIneligible;
    final showDiscountInfo = discountEligible || panel.discountOverride != 0;
    final canEditNetAmount = panel.amountValue != null;
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
            if (showDiscountInfo)
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
                if (discountEligible) ...[
                  Expanded(
                    child: OutlinedButton(
                      onPressed: state.isBusy ? null : _toggleDiscount,
                      child:
                          Text(panel.isDiscountExcluded ? '할인 적용' : '할인 제외'),
                    ),
                  ),
                  const SizedBox(width: 10),
                ],
                if (canEditNetAmount) ...[
                  Expanded(
                    child: OutlinedButton(
                      onPressed:
                          state.isBusy ? null : () => _editNetAmount(context),
                      child: const Text('실결제액 수정'),
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
    if (panel.isDiscountIneligible) return;
    if (panel.isDiscountExcluded) {
      await state.applyDefaultPanelDiscount(panel.id);
    } else {
      await state.excludeExistingPanelDiscount(panel.id);
    }
  }

  Future<void> _editNetAmount(BuildContext context) async {
    final amount = panel.amountValue;
    if (amount == null) return;
    final controller = TextEditingController(
      text: panel.effectiveAmountForPolicy(discountPolicyEnabled).toString(),
    );
    final netAmount = await showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(isClaim ? '실청구액 수정' : '실결제액 수정'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          autofocus: true,
          decoration: InputDecoration(
            labelText: isClaim ? '실청구액' : '실결제액',
          ),
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
    await state.updatePanelNetAmount(panel, netAmount);
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
