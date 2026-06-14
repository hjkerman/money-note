import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../notification_bridge.dart';
import '../theme.dart';
import '../widgets/money_card.dart';

class NotificationImportScreen extends StatefulWidget {
  const NotificationImportScreen({required this.state, super.key});

  final AppState state;

  @override
  State<NotificationImportScreen> createState() =>
      _NotificationImportScreenState();
}

class _NotificationImportScreenState extends State<NotificationImportScreen> {
  final bridge = NotificationBridge();
  late Future<List<PendingCardNotification>> pendingFuture;

  @override
  void initState() {
    super.initState();
    pendingFuture = bridge.listPending();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('알림에서 가져오기')),
      body: FutureBuilder<List<PendingCardNotification>>(
        future: pendingFuture,
        builder: (context, snapshot) {
          final items = snapshot.data ?? [];
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              MoneyCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('카드사 알림 보관함',
                        style: TextStyle(
                            fontSize: 22, fontWeight: FontWeight.w900)),
                    const SizedBox(height: 10),
                    const Text(
                      '우리카드 알림만 읽고, 원문은 저장하지 않습니다. 등록 전까지는 서버에 보내지 않습니다.',
                      style: TextStyle(
                          color: moneyMuted, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton(
                        onPressed: bridge.openSettings,
                        child: const Text('알림 접근 권한 열기')),
                  ],
                ),
              ),
              const SectionTitle('등록 대기 후보'),
              if (snapshot.connectionState == ConnectionState.waiting)
                const Center(
                    child: Padding(
                        padding: EdgeInsets.all(24),
                        child: CircularProgressIndicator()))
              else if (items.isEmpty)
                const MoneyCard(child: Text('등록 대기 중인 카드 알림이 없습니다.'))
              else
                ...items.map((item) => _PendingCandidateCard(
                      state: widget.state,
                      bridge: bridge,
                      candidate: item,
                      onChanged: _reload,
                    )),
            ],
          );
        },
      ),
    );
  }

  void _reload() {
    setState(() {
      pendingFuture = bridge.listPending();
    });
  }
}

class _PendingCandidateCard extends StatefulWidget {
  const _PendingCandidateCard({
    required this.state,
    required this.bridge,
    required this.candidate,
    required this.onChanged,
  });

  final AppState state;
  final NotificationBridge bridge;
  final PendingCardNotification candidate;
  final VoidCallback onChanged;

  @override
  State<_PendingCandidateCard> createState() => _PendingCandidateCardState();
}

class _PendingCandidateCardState extends State<_PendingCandidateCard> {
  late final TextEditingController place;
  late final TextEditingController item;
  late final TextEditingController amount;
  late String target;
  late bool discountEnabled;

  @override
  void initState() {
    super.initState();
    place = TextEditingController(text: widget.candidate.usagePlace);
    item = TextEditingController();
    amount = TextEditingController(text: widget.candidate.amount.toString());
    target = _initialTarget();
    discountEnabled = _defaultDiscountEnabled(target);
  }

  @override
  void dispose() {
    place.dispose();
    item.dispose();
    amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final unknown = target == 'unknown';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: MoneyCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                      '${widget.candidate.monthDay} ${widget.candidate.time}',
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                ),
                Text(won(int.tryParse(amount.text) ?? widget.candidate.amount),
                    style: const TextStyle(
                        fontSize: 17, fontWeight: FontWeight.w900)),
              ],
            ),
            const SizedBox(height: 8),
            Text('카드 ${widget.candidate.cardLast4}',
                style: const TextStyle(color: moneyMuted)),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'owner', label: Text('내 카드')),
                ButtonSegment(value: 'family_card', label: Text('가족카드')),
                ButtonSegment(value: 'unknown', label: Text('미식별')),
              ],
              selected: {target},
              onSelectionChanged: (value) => setState(() {
                target = value.first;
                discountEnabled = _defaultDiscountEnabled(target);
              }),
            ),
            const SizedBox(height: 12),
            TextField(
                controller: place,
                decoration: const InputDecoration(labelText: '사용처')),
            const SizedBox(height: 10),
            TextField(
                controller: item,
                decoration: const InputDecoration(labelText: '사용항목')),
            const SizedBox(height: 10),
            TextField(
                controller: amount,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: '금액')),
            if (!unknown) ...[
              const SizedBox(height: 8),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('할인 적용'),
                value: discountEnabled,
                onChanged: (value) =>
                    setState(() => discountEnabled = value ?? false),
              ),
            ],
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed:
                        unknown || widget.state.isBusy ? null : _register,
                    child: const Text('등록'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: _delete,
                    style: OutlinedButton.styleFrom(foregroundColor: moneyRed),
                    child: const Text('삭제'),
                  ),
                ),
              ],
            ),
            if (unknown)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text('카드 식별 불가: 내 카드 또는 가족카드를 직접 선택하세요.',
                    style: TextStyle(color: moneyRed)),
              ),
          ],
        ),
      ),
    );
  }

  String _initialTarget() {
    if (widget.candidate.cardLast4 == widget.state.settings.ownerCardLast4) {
      return 'owner';
    }
    if (widget.candidate.cardLast4 == widget.state.settings.familyCardLast4) {
      return 'family_card';
    }
    return 'unknown';
  }

  bool _defaultDiscountEnabled(String target) {
    if (target == 'family_card') {
      return widget.state.familyDiscountMonth?.isEnabled ?? false;
    }
    if (target == 'owner') {
      return widget.state.ownerDiscountMonth?.isEnabled ?? true;
    }
    return false;
  }

  Future<void> _register() async {
    final parsedAmount = int.tryParse(amount.text.replaceAll(',', '').trim());
    if (place.text.trim().isEmpty || parsedAmount == null || parsedAmount < 0) {
      return;
    }
    final updated = PendingCardNotification(
      id: widget.candidate.id,
      cardLast4: widget.candidate.cardLast4,
      monthDay: widget.candidate.monthDay,
      time: widget.candidate.time,
      amount: parsedAmount,
      usagePlace: place.text.trim(),
    );
    await widget.state.registerNotificationCandidate(
      candidate: updated,
      usageItem: item.text,
      target: target,
      discountEnabled: discountEnabled,
    );
    await widget.bridge.deletePending(widget.candidate.id);
    widget.onChanged();
  }

  Future<void> _delete() async {
    await widget.bridge.deletePending(widget.candidate.id);
    widget.onChanged();
  }
}
