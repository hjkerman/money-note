import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'notification_import_screen.dart';
import 'snapshot_manager_screen.dart';

class ManagementScreen extends StatelessWidget {
  const ManagementScreen({required this.state, super.key});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('관리')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
        children: [
          const MoneyCard(
            child: Text(
              '자주 쓰지 않는 조작을 모았습니다. 일상 입력 흐름과 분리해두는 쪽이 장부가 덜 산만합니다.',
              style: TextStyle(color: moneyMuted, fontWeight: FontWeight.w600),
            ),
          ),
          const SizedBox(height: 14),
          ManagementMenuList(state: state),
        ],
      ),
    );
  }
}

class ManagementMenuList extends StatelessWidget {
  const ManagementMenuList({required this.state, super.key});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _MenuCard(
          title: '동결 금액',
          subtitle: '당장 쓰지 않을 금액을 등록하거나 삭제합니다.',
          icon: Icons.lock_outline,
          onTap: () => _push(
            context,
            PanelManagementScreen(
              state: state,
              panelType: 'frozen',
              title: '동결 금액',
              inputLabel: '동결 내용',
              emptyText: '동결 금액이 없습니다.',
            ),
          ),
        ),
        _MenuCard(
          title: '현금성 고정지출',
          subtitle: '이번 달 현금성으로 빼둘 고정지출을 관리합니다.',
          icon: Icons.savings_outlined,
          onTap: () => _push(
            context,
            PanelManagementScreen(
              state: state,
              panelType: 'fixed',
              title: '현금성 고정지출',
              inputLabel: '지출 내용',
              emptyText: '현금성 고정지출이 없습니다.',
            ),
          ),
        ),
        _MenuCard(
          title: '카드 정기결제',
          subtitle: '매달 카드로 나갈 정기결제를 등록하고 확인 처리합니다.',
          icon: Icons.credit_card,
          onTap: () =>
              _push(context, PlannedEntryManagementScreen(state: state)),
        ),
        _MenuCard(
          title: '월마감',
          subtitle: '현재 월마감 가능 여부를 확인하고 실행합니다.',
          icon: Icons.event_available,
          onTap: () => _push(context, MonthCloseManagementScreen(state: state)),
        ),
        _MenuCard(
          title: '백업 / 복원',
          subtitle: '앱 내부 스냅샷을 공유하거나 복원합니다.',
          icon: Icons.backup_outlined,
          onTap: () => _push(context, SnapshotManagerScreen(state: state)),
        ),
        _MenuCard(
          title: '설정',
          subtitle: '카드번호 4자리와 기본 운영 설정을 관리합니다.',
          icon: Icons.settings_outlined,
          onTap: () => _push(context, MobileSettingsScreen(state: state)),
        ),
        _MenuCard(
          title: '최근 우리카드 알림',
          subtitle: '실사용 중인 우리카드 승인 알림 원문을 확인하고 공유합니다.',
          icon: Icons.notifications_active_outlined,
          onTap: () => _push(context, WooriNotificationLogScreen(state: state)),
        ),
        _MenuCard(
          title: 'Experimental Data',
          subtitle: '교통·통행 원문을 보관하는 실험용 관측소입니다.',
          icon: Icons.science_outlined,
          onTap: () => _push(context, ExperimentalDataScreen(state: state)),
        ),
      ],
    );
  }

  void _push(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }
}

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
        final total =
            rows.fold<int>(0, (sum, panel) => sum + (panel.amountValue ?? 0));
        return Scaffold(
          appBar: AppBar(title: Text(widget.title)),
          body: RefreshIndicator(
            onRefresh: widget.state.refreshPanelManagementArea,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
              children: [
                AmountTile(label: '합계', amount: won(total)),
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
                          onPressed: widget.state.isBusy ? null : _submit,
                          child: const Text('추가')),
                    ],
                  ),
                ),
                SectionTitle('목록',
                    trailing: Text('${rows.length}건',
                        style: const TextStyle(color: moneyMuted))),
                if (rows.isEmpty) MoneyCard(child: Text(widget.emptyText)),
                ...rows.map((panel) => _PanelManagementItem(
                      panel: panel,
                      state: widget.state,
                    )),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _submit() async {
    final parsedAmount = int.tryParse(amount.text.replaceAll(',', '').trim());
    if (title.text.trim().isEmpty || parsedAmount == null || parsedAmount < 0) {
      return;
    }
    await widget.state.createPanel(
      panelType: widget.panelType,
      title: title.text,
      amount: parsedAmount,
      discountEnabled: true,
    );
    title.clear();
    amount.clear();
  }
}

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
                          onPressed: widget.state.isBusy ? null : _submit,
                          child: const Text('정기결제 추가')),
                    ],
                  ),
                ),
                SectionTitle('목록',
                    trailing: Text('${rows.length}건',
                        style: const TextStyle(color: moneyMuted))),
                if (rows.isEmpty)
                  const MoneyCard(child: Text('카드 정기결제가 없습니다.')),
                ...rows.map((entry) =>
                    _PlannedEntryItem(entry: entry, state: widget.state)),
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
    final parsedDueDay = int.tryParse(dueDay.text.trim());
    final parsedAmount = int.tryParse(amount.text.replaceAll(',', '').trim());
    if (parsedDueDay == null ||
        parsedDueDay < 1 ||
        parsedDueDay > 31 ||
        usagePlace.text.trim().isEmpty ||
        parsedAmount == null ||
        parsedAmount < 0) {
      return;
    }
    await widget.state.createPlannedEntry(
      dueDay: parsedDueDay,
      usagePlace: usagePlace.text,
      usageItem: usageItem.text,
      amount: parsedAmount,
    );
    dueDay.clear();
    usagePlace.clear();
    usageItem.clear();
    amount.clear();
  }
}

class MonthCloseManagementScreen extends StatelessWidget {
  const MonthCloseManagementScreen({required this.state, super.key});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final status = state.monthCloseStatus;
    final canClose = status?.canClose ?? false;
    return Scaffold(
      appBar: AppBar(title: const Text('월마감')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
        children: [
          MoneyCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Line(label: '서버 기준 날짜', value: status?.calendarDate ?? '-'),
                _Line(label: '마감 대상', value: status?.oldestOpenMonth ?? '-'),
                _Line(label: '마감 가능', value: canClose ? '가능' : '아직 아님'),
                const SizedBox(height: 12),
                Text(
                  canClose
                      ? '월마감은 복원 전 백업을 먼저 남긴 뒤 실행됩니다.'
                      : '월마감은 서버 기준으로 가능한 때에만 사용할 수 있습니다.',
                  style: const TextStyle(
                      color: moneyMuted, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          FilledButton(
            onPressed: state.isBusy || !canClose
                ? null
                : () => _confirmMonthClose(context),
            child: const Text('월마감 실행'),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmMonthClose(BuildContext context) async {
    final status = state.monthCloseStatus;
    final targetMonth = status?.oldestOpenMonth;
    final isEarlyClose = status?.isEarlyClose ?? false;
    final firstConfirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('월마감'),
        content: Text(targetMonth == null
            ? '현재 열린 월을 마감할까요?'
            : '$targetMonth 기록을 월마감할까요?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('계속'),
          ),
        ],
      ),
    );
    if (firstConfirmed != true || !context.mounted) return;
    final finalConfirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('정말 월마감'),
        content: const Text('마감 후에는 이번 달 기록이 전체 기록으로 이동합니다. 정말 진행할까요?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('마감 실행'),
          ),
        ],
      ),
    );
    if (finalConfirmed == true) {
      await state.closeCurrentMonth(allowEarlyClose: isEarlyClose);
    }
  }
}

class MobileSettingsScreen extends StatefulWidget {
  const MobileSettingsScreen({required this.state, super.key});

  final AppState state;

  @override
  State<MobileSettingsScreen> createState() => _MobileSettingsScreenState();
}

class _MobileSettingsScreenState extends State<MobileSettingsScreen> {
  late final TextEditingController ownerCard;
  late final TextEditingController familyCard;
  late final TextEditingController cardLimit;
  late final TextEditingController baseIncome;
  late final TextEditingController interestExpense;

  @override
  void initState() {
    super.initState();
    final settings = widget.state.settings.values;
    ownerCard = TextEditingController(text: settings['owner_card_last4'] ?? '');
    familyCard =
        TextEditingController(text: settings['family_card_last4'] ?? '');
    cardLimit = TextEditingController(text: settings['card_limit'] ?? '');
    baseIncome = TextEditingController(
        text: settings['base_next_month_liquidity'] ?? '');
    interestExpense =
        TextEditingController(text: settings['interest_expense'] ?? '');
  }

  @override
  void dispose() {
    ownerCard.dispose();
    familyCard.dispose();
    cardLimit.dispose();
    baseIncome.dispose();
    interestExpense.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
        children: [
          _SettingField(
            controller: ownerCard,
            label: '본인 카드번호 뒤 4자리',
            keyboardType: TextInputType.number,
            onSave: () => _save('owner_card_last4', ownerCard.text),
          ),
          _SettingField(
            controller: familyCard,
            label: '가족카드 번호 뒤 4자리',
            keyboardType: TextInputType.number,
            onSave: () => _save('family_card_last4', familyCard.text),
          ),
          _SettingField(
            controller: cardLimit,
            label: '카드 한도',
            keyboardType: TextInputType.number,
            onSave: () => _save('card_limit', cardLimit.text),
          ),
          _SettingField(
            controller: baseIncome,
            label: '기본 예정 수입',
            keyboardType: TextInputType.number,
            onSave: () => _save('base_next_month_liquidity', baseIncome.text),
          ),
          _SettingField(
            controller: interestExpense,
            label: '이자 지출',
            keyboardType: TextInputType.number,
            onSave: () => _save('interest_expense', interestExpense.text),
          ),
        ],
      ),
    );
  }

  Future<void> _save(String key, String value) async {
    await widget.state.updateSetting(key, value.trim());
  }
}

class _MenuCard extends StatelessWidget {
  const _MenuCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Row(
              children: [
                Icon(icon, color: moneyGreen),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title,
                          style: const TextStyle(
                              fontSize: 17, fontWeight: FontWeight.w900)),
                      const SizedBox(height: 4),
                      Text(subtitle,
                          style: const TextStyle(
                              color: moneyMuted, fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right, color: moneyMuted),
              ],
            ),
          ),
        ),
      ),
    );
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
              onPressed:
                  state.isBusy ? null : () => state.deletePanel(panel.id),
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

class _PlannedEntryItem extends StatefulWidget {
  const _PlannedEntryItem({required this.entry, required this.state});

  final LedgerEntry entry;
  final AppState state;

  @override
  State<_PlannedEntryItem> createState() => _PlannedEntryItemState();
}

class _PlannedEntryItemState extends State<_PlannedEntryItem> {
  late String entryDate;

  @override
  void initState() {
    super.initState();
    entryDate = _plannedEntryDefaultDate(
        widget.state.currentMonth, widget.entry.dueDay);
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
            _DatePickerRow(
              label: '이번 등록 날짜',
              value: entryDate,
              onChanged: (value) => setState(() => entryDate = value),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: state.isBusy
                        ? null
                        : () => state.confirmPlannedEntry(entry.id, entryDate),
                    child: const Text('확인 처리'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: state.isBusy
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
            Text('${entry.dueDay ?? '-'}일 ${entry.usagePlace ?? entry.title}',
                style:
                    const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
            if ((entry.usageItem ?? '').isNotEmpty)
              Text(entry.usageItem!, style: const TextStyle(color: moneyMuted)),
            const SizedBox(height: 8),
            _Line(label: '예정액', value: won(entry.amountValue)),
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

class _SettingField extends StatelessWidget {
  const _SettingField({
    required this.controller,
    required this.label,
    required this.keyboardType,
    required this.onSave,
  });

  final TextEditingController controller;
  final String label;
  final TextInputType keyboardType;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                keyboardType: keyboardType,
                decoration: InputDecoration(labelText: label),
              ),
            ),
            const SizedBox(width: 10),
            FilledButton(onPressed: onSave, child: const Text('저장')),
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
      padding: const EdgeInsets.symmetric(vertical: 4),
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
