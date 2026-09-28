part of 'management_screen.dart';

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
  late bool transitFollowsOwner;

  @override
  void initState() {
    super.initState();
    final settings = widget.state.settings.values;
    ownerCard = TextEditingController(text: settings['owner_card_last4'] ?? '');
    familyCard =
        TextEditingController(text: settings['family_card_last4'] ?? '');
    cardLimit = TextEditingController(text: settings['card_limit'] ?? '');
    baseIncome =
        TextEditingController(text: settings['scheduled_income'] ?? '');
    transitFollowsOwner =
        widget.state.transitDiscountProfile?.followsOwner ?? false;
  }

  @override
  void dispose() {
    ownerCard.dispose();
    familyCard.dispose();
    cardLimit.dispose();
    baseIncome.dispose();
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
            onSave: widget.state.canUseOnlineWrites
                ? () => _save('owner_card_last4', ownerCard.text)
                : null,
          ),
          _SettingField(
            controller: familyCard,
            label: '가족카드 번호 뒤 4자리',
            keyboardType: TextInputType.number,
            onSave: widget.state.canUseOnlineWrites
                ? () => _save('family_card_last4', familyCard.text)
                : null,
          ),
          _SettingField(
            controller: cardLimit,
            label: '카드 한도',
            keyboardType: TextInputType.number,
            onSave: widget.state.canUseOnlineWrites
                ? () => _save('card_limit', cardLimit.text)
                : null,
          ),
          _SettingField(
            controller: baseIncome,
            label: '기본 예정 수입',
            keyboardType: TextInputType.number,
            onSave: widget.state.canUseOnlineWrites
                ? () => _save('scheduled_income', baseIncome.text)
                : null,
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: MoneyCard(
              child: SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text(
                  '교통카드 할인',
                  style: TextStyle(fontWeight: FontWeight.w900),
                ),
                subtitle: const Text(
                  '이번 달부터 본인카드의 할인 계산식과 월별 혜택 여부를 함께 따릅니다.',
                ),
                value: transitFollowsOwner,
                onChanged: widget.state.canUseOnlineWrites ? _setTransitProfile : null,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _save(String key, String value) async {
    await widget.state.updateSetting(key, value.trim());
  }

  Future<void> _setTransitProfile(bool value) async {
    setState(() => transitFollowsOwner = value);
    await widget.state.updateTransitDiscountProfile(value);
    if (!mounted) return;
    setState(() {
      transitFollowsOwner =
          widget.state.transitDiscountProfile?.followsOwner ?? false;
    });
  }
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
  final VoidCallback? onSave;

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
                enabled: onSave != null,
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
