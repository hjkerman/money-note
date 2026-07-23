import 'package:flutter/material.dart';

import '../app_state.dart';
import '../models.dart';
import '../notification_bridge.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'notification_archive_screen.dart';

class NotificationImportScreen extends StatefulWidget {
  const NotificationImportScreen({required this.state, super.key});

  final AppState state;

  @override
  State<NotificationImportScreen> createState() =>
      _NotificationImportScreenState();
}

class _NotificationImportScreenState extends State<NotificationImportScreen> {
  final bridge = NotificationBridge();
  late Future<_NotificationInboxData> inboxFuture;
  bool manualNoticeDismissed = false;

  @override
  void initState() {
    super.initState();
    inboxFuture = _load();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_NotificationInboxData>(
      future: inboxFuture,
      builder: (context, snapshot) {
        final data = snapshot.data ?? const _NotificationInboxData.empty();
        final owner =
            data.candidates.where((item) => item.isOwnerCard).toList();
        final family =
            data.candidates.where((item) => item.isFamilyCard).toList();
        final manualCount =
            data.logs.where((item) => item.needsManualReview).length;
        return DefaultTabController(
          length: 2,
          child: Scaffold(
            appBar: AppBar(
              title: const Text('알림에서 가져오기'),
              bottom: TabBar(
                tabs: [
                  Tab(text: '본인카드(${owner.length})'),
                  Tab(text: '가족카드(${family.length})'),
                ],
              ),
            ),
            body: RefreshIndicator(
              onRefresh: () async => _reload(),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
                children: [
                  if (manualCount > 0 && !manualNoticeDismissed)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: FilledButton.tonal(
                        onPressed: () async {
                          setState(() => manualNoticeDismissed = true);
                          await Navigator.of(context).push(MaterialPageRoute(
                            builder: (_) =>
                                WooriNotificationLogScreen(state: widget.state),
                          ));
                          await _reload();
                        },
                        child: Text('직접 확인 필요!($manualCount건)'),
                      ),
                    ),
                  SizedBox(
                    height: MediaQuery.of(context).size.height - 190,
                    child: TabBarView(
                      children: [
                        _CandidateList(
                          state: widget.state,
                          bridge: bridge,
                          role: 'owner',
                          candidates: owner,
                          onChanged: _reload,
                        ),
                        _CandidateList(
                          state: widget.state,
                          bridge: bridge,
                          role: 'family',
                          candidates: family,
                          onChanged: _reload,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<_NotificationInboxData> _load() async {
    final results = await Future.wait([
      bridge.listCandidates(),
      bridge.listWooriLogs(),
    ]);
    return _NotificationInboxData(
      candidates: results[0] as List<CardNotificationCandidate>,
      logs: results[1] as List<CapturedNotificationLog>,
    );
  }

  Future<void> _reload() async {
    await widget.state.refreshNotificationInboxState(notify: true);
    setState(() {
      inboxFuture = _load();
    });
  }
}

class _CandidateList extends StatelessWidget {
  const _CandidateList({
    required this.state,
    required this.bridge,
    required this.role,
    required this.candidates,
    required this.onChanged,
  });

  final AppState state;
  final NotificationBridge bridge;
  final String role;
  final List<CardNotificationCandidate> candidates;
  final Future<void> Function() onChanged;

  @override
  Widget build(BuildContext context) {
    final title = role == 'family' ? '가족카드 후보' : '본인카드 후보';
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        SectionTitle(title,
            trailing: Text('${candidates.length}건',
                style: const TextStyle(color: moneyMuted))),
        if (candidates.isEmpty)
          const MoneyCard(child: Text('등록 대기 중인 승인 알림이 없습니다.'))
        else
          ...candidates.map((candidate) => _CandidateCard(
                key: ValueKey(candidate.id),
                state: state,
                bridge: bridge,
                candidate: candidate,
                onChanged: onChanged,
              )),
        const SizedBox(height: 12),
        OutlinedButton(
          onPressed: candidates.isEmpty
              ? null
              : () async {
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: Text('$title 전체 삭제'),
                      content: const Text(
                          '이 탭의 후보를 모두 삭제할까요? 서버에는 아무 것도 전송하지 않습니다.'),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.of(context).pop(false),
                          child: const Text('취소'),
                        ),
                        FilledButton(
                          onPressed: () => Navigator.of(context).pop(true),
                          child: const Text('전체 삭제'),
                        ),
                      ],
                    ),
                  );
                  if (confirmed != true) return;
                  await bridge.clearCandidatesByRole(role);
                  await onChanged();
                },
          child: Text('$title 전체 삭제'),
        ),
      ],
    );
  }
}

class _CandidateCard extends StatefulWidget {
  const _CandidateCard({
    super.key,
    required this.state,
    required this.bridge,
    required this.candidate,
    required this.onChanged,
  });

  final AppState state;
  final NotificationBridge bridge;
  final CardNotificationCandidate candidate;
  final Future<void> Function() onChanged;

  @override
  State<_CandidateCard> createState() => _CandidateCardState();
}

class _CandidateCardState extends State<_CandidateCard> {
  late final TextEditingController date;
  late final TextEditingController place;
  late final TextEditingController item;
  late final TextEditingController amount;
  late String target;
  bool? discountEnabled;
  String? spendingCategory;

  @override
  void initState() {
    super.initState();
    date = TextEditingController(text: widget.candidate.entryDate);
    place = TextEditingController(text: widget.candidate.merchant);
    item = TextEditingController();
    amount = TextEditingController(text: widget.candidate.amount.toString());
    target = widget.candidate.isFamilyCard ? 'family_card' : 'ledger';
  }

  @override
  void dispose() {
    date.dispose();
    place.dispose();
    item.dispose();
    amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final showCategory = target == 'ledger';
    final discountValue = discountEnabled ?? _defaultDiscountEnabled();
    final targetOptions = widget.candidate.isFamilyCard
        ? const [
            ButtonSegment(value: 'family_card', label: Text('가족 사용')),
            ButtonSegment(value: 'ledger', label: Text('본인 사용')),
          ]
        : const [
            ButtonSegment(value: 'ledger', label: Text('본인 사용')),
            ButtonSegment(value: 'claim', label: Text('청구 사용')),
          ];
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('카드 ${widget.candidate.cardLast4}',
                style:
                    const TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: targetOptions,
              selected: {target},
              onSelectionChanged: (value) {
                setState(() {
                  target = value.first;
                  discountEnabled = null;
                });
              },
            ),
            const SizedBox(height: 12),
            TextField(
              controller: date,
              decoration: const InputDecoration(labelText: '날짜'),
              keyboardType: TextInputType.datetime,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: place,
              decoration: const InputDecoration(labelText: '사용처'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: item,
              decoration: const InputDecoration(labelText: '사용항목'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: amount,
              decoration: const InputDecoration(labelText: '금액'),
              keyboardType: TextInputType.number,
            ),
            if (showCategory) ...[
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
                onChanged: (value) => setState(() => spendingCategory = value),
              ),
            ],
            const SizedBox(height: 8),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('할인 적용'),
              value: discountValue,
              onChanged: (value) =>
                  setState(() => discountEnabled = value ?? false),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    onPressed: widget.state.isBusy ? null : _register,
                    child: const Text('등록'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: _delete,
                    child: const Text('삭제'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(widget.candidate.rawText,
                style: const TextStyle(color: moneyMuted, fontSize: 12)),
          ],
        ),
      ),
    );
  }

  bool _defaultDiscountEnabled() {
    if (target == 'family_card') {
      return widget.state.familyDiscountMonth?.isEnabled ?? false;
    }
    return widget.state.ownerDiscountMonth?.isEnabled ?? true;
  }

  Future<void> _register() async {
    final parsedAmount = int.tryParse(amount.text.replaceAll(',', '').trim());
    if (date.text.trim().isEmpty ||
        place.text.trim().isEmpty ||
        parsedAmount == null ||
        parsedAmount < 0) {
      return;
    }

    final success = target == 'ledger'
        ? await widget.state.createExpense(
            usagePlace: place.text,
            usageItem: item.text,
            amount: parsedAmount,
            discountEnabled: discountEnabled ?? _defaultDiscountEnabled(),
            spendingCategory: spendingCategory,
            entryDate: date.text.trim(),
          )
        : await widget.state.createPanel(
            panelType: target,
            title: _panelTitle(place.text, item.text),
            amount: parsedAmount,
            discountEnabled: discountEnabled ?? _defaultDiscountEnabled(),
            spentOn: date.text.trim(),
          );
    if (!success) return;
    await widget.bridge.deleteCandidate(widget.candidate.id);
    await widget.onChanged();
  }

  Future<void> _delete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('후보 삭제'),
        content: Text('${place.text} 후보를 삭제할까요?'),
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
    if (confirmed != true) return;
    await widget.bridge.deleteCandidate(widget.candidate.id);
    await widget.onChanged();
  }

  String _panelTitle(String usagePlace, String usageItem) {
    final trimmedPlace = usagePlace.trim();
    final trimmedItem = usageItem.trim();
    if (trimmedItem.isEmpty) return trimmedPlace;
    if (target == 'claim') return '$trimmedPlace: $trimmedItem';
    return '[$trimmedPlace] $trimmedItem';
  }
}

class _NotificationInboxData {
  const _NotificationInboxData({required this.candidates, required this.logs});

  const _NotificationInboxData.empty()
      : candidates = const [],
        logs = const [];

  final List<CardNotificationCandidate> candidates;
  final List<CapturedNotificationLog> logs;
}
