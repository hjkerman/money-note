import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'notification_import_screen.dart';

class InputScreen extends StatefulWidget {
  const InputScreen({required this.state, super.key, this.onJudgmentTap});

  final AppState state;
  final VoidCallback? onJudgmentTap;

  @override
  State<InputScreen> createState() => _InputScreenState();
}

class _InputScreenState extends State<InputScreen> {
  final place = TextEditingController();
  final item = TextEditingController();
  final amount = TextEditingController();
  final placeFocus = FocusNode();
  bool? discountEnabled;
  String? spendingCategory;
  late String selectedDate;

  @override
  void initState() {
    super.initState();
    selectedDate = widget.state.serverToday;
  }

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
    final discountValue =
        discountEnabled ?? (widget.state.ownerDiscountMonth?.isEnabled ?? true);
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
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
        const SectionTitle('오늘의 예산심사위원회'),
        _JudgmentPreviewCard(
          message: widget.state.judgment?.budget.message ?? '',
          onTap: widget.onJudgmentTap,
        ),
        if (!widget.state.notificationPermissions.isReady)
          _PermissionWarningCard(state: widget.state),
        const SectionTitle('카드 지출 입력'),
        MoneyCard(
          child: Column(
            children: [
              _DatePickerRow(
                label: '사용 일자',
                value: selectedDate,
                onChanged: (value) => setState(() => selectedDate = value),
              ),
              const SizedBox(height: 12),
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
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: spendingCategory,
                decoration: const InputDecoration(labelText: '분류'),
                items: spendingCategoryOptions
                    .map((option) => DropdownMenuItem<String>(
                          value: option.value,
                          child: Text(option.label),
                        ))
                    .toList(),
                onChanged: (value) => setState(() {
                  spendingCategory = value;
                }),
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
              const SizedBox(height: 16),
              ElevatedButton(
                  onPressed: widget.state.isBusy ? null : _submit,
                  child: const Text('지출 추가')),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                      builder: (_) =>
                          NotificationImportScreen(state: widget.state)),
                ),
                child: Text(_notificationButtonText(widget.state)),
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
      discountEnabled: discountEnabled ??
          (widget.state.ownerDiscountMonth?.isEnabled ?? true),
      spendingCategory: spendingCategory,
      entryDate: selectedDate,
    );
    place.clear();
    item.clear();
    amount.clear();
    spendingCategory = null;
    setState(() => selectedDate = widget.state.serverToday);
    placeFocus.requestFocus();
  }
}

String _notificationButtonText(AppState state) {
  final counts = state.notificationCandidateCounts;
  if (counts.total == 0) return '알림에서 가져오기';
  return '알림에서 가져오기(${counts.total}) · 본인 ${counts.owner}건 / 가족 ${counts.family}건';
}

class _JudgmentPreviewCard extends StatelessWidget {
  const _JudgmentPreviewCard({required this.message, this.onTap});

  final String message;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final text = message.trim().isEmpty ? '판단 결과를 불러오는 중입니다.' : message.trim();
    return MoneyCard(
      color: moneyGreenSoft,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Row(
          children: [
            const Icon(Icons.gavel, color: moneyGreen),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                text,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style:
                    const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
              ),
            ),
            if (onTap != null) ...[
              const SizedBox(width: 8),
              const Icon(Icons.chevron_right, color: moneyMuted),
            ],
          ],
        ),
      ),
    );
  }
}

class _PermissionWarningCard extends StatelessWidget {
  const _PermissionWarningCard({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final permissions = state.notificationPermissions;
    final missing = [
      if (!permissions.listenerEnabled) '알림 접근 권한',
      if (!permissions.appNotificationsEnabled) '앱 알림 표시 권한',
      if (!permissions.batteryUnrestricted) '배터리 사용량 제한없음',
    ].join(', ');

    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: MoneyCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('카드 알림 낚시 준비가 덜 됐습니다.',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
            const SizedBox(height: 6),
            Text('앱을 사용하려면 $missing을 허용해야 합니다.',
                style: const TextStyle(color: moneyMuted)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (!permissions.listenerEnabled)
                  OutlinedButton(
                    onPressed: state.openNotificationListenerSettings,
                    child: const Text('알림 접근 열기'),
                  ),
                if (!permissions.appNotificationsEnabled)
                  OutlinedButton(
                    onPressed: state.requestAppNotifications,
                    child: const Text('앱 알림 허용'),
                  ),
                if (!permissions.batteryUnrestricted)
                  OutlinedButton(
                    onPressed: state.openBatteryOptimizationSettings,
                    child: const Text('배터리 제한 해제'),
                  ),
                TextButton(
                  onPressed: state.refreshNotificationPermissions,
                  child: const Text('다시 확인'),
                ),
              ],
            ),
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
