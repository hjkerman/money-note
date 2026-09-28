import 'package:flutter/material.dart';

import '../app_state.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import '../widgets/date_picker_row.dart';
import 'notification_archive_screen.dart';
import 'snapshot_manager_screen.dart';

part 'management_panel.dart';
part 'management_planned.dart';
part 'management_month_close.dart';
part 'management_settings.dart';

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
          title: '최근 납치한 알림',
          subtitle: '우리카드와 통행료 알림 원문 및 파싱 결과를 확인합니다.',
          icon: Icons.notifications_active_outlined,
          onTap: () => _push(
            context,
            CapturedNotificationLogScreen(state: state),
          ),
        ),
      ],
    );
  }

  void _push(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
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
