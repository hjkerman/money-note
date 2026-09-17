import 'package:flutter/material.dart';

import '../app_state.dart';
import '../apk_download_controller.dart';
import '../apk_download_service.dart';
import '../formatters.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'management_screen.dart';

class StatusScreen extends StatelessWidget {
  const StatusScreen({
    required this.state,
    required this.apkDownloadController,
    super.key,
  });

  final AppState state;
  final ApkDownloadController apkDownloadController;

  @override
  Widget build(BuildContext context) {
    final summary = state.summary;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 54, 20, 96),
      children: [
        Row(
          children: [
            const Expanded(
                child: Text('설정',
                    style:
                        TextStyle(fontSize: 24, fontWeight: FontWeight.w900))),
            IconButton(
                onPressed: state.canUseOnlineWrites ? state.logout : null,
                icon: const Icon(Icons.logout),
                tooltip: '로그아웃'),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
                child: AmountTile(
                    label: state.financialValuesAreEstimated ? '카드대금(예상)' : '카드대금',
                    amount: won(summary?.cardTotal))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(
                    label: state.financialValuesAreEstimated ? '월 지출(예상)' : '월 지출',
                    amount: won(summary?.currentSpendingTotal))),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
                child: AmountTile(
                    label: state.financialValuesAreEstimated
                        ? '잔여 유동성(예상)'
                        : '잔여 유동성',
                    amount: won(summary?.remainingLiquidity))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(
                    label: '동결', amount: won(summary?.frozenAssetTotal))),
          ],
        ),
        if (state.isOnline) ...[
          const SizedBox(height: 14),
          OutlinedButton.icon(
            onPressed: state.isBusy ? null : () => _enterOffline(context),
            icon: const Icon(Icons.cloud_off),
            label: const Text('오프라인 모드 시작'),
          ),
        ],
        const SectionTitle('관리'),
        ManagementMenuList(state: state),
        if (state.statusMessage.isNotEmpty) ...[
          const SizedBox(height: 14),
          Text(state.statusMessage, style: const TextStyle(color: moneyMuted)),
        ],
        const SizedBox(height: 24),
        _ApkDownloadButton(
          state: state,
          controller: apkDownloadController,
        ),
      ],
    );
  }

  Future<void> _enterOffline(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('오프라인 모드 시작'),
        content: const Text(
          '마지막 정상 동기화 상태로 전환합니다. 서버 연결이 복구되면 자동 동기화하지 않고 조정 화면으로 이동합니다.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('시작'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    final entered = await state.enterOfflineMode();
    if (!entered && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(state.offlineEntryMessage)),
      );
    }
  }
}

class _ApkDownloadButton extends StatelessWidget {
  const _ApkDownloadButton({
    required this.state,
    required this.controller,
  });

  final AppState state;
  final ApkDownloadController controller;

  Future<void> _download(BuildContext context) async {
    try {
      await controller.download(state.api);
    } on ApkDownloadException catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final progress = controller.progress;
        final label = !controller.isDownloading
            ? 'APK 다운로드'
            : progress == null
                ? 'APK 받는 중...'
                : 'APK 받는 중 ${(progress * 100).round()}%';
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (controller.installedVersion case final version?) ...[
              Text(
                '현재 설치 버전 ${version.label}',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: moneyMuted,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
            ],
            FilledButton.icon(
              onPressed: controller.isDownloading || !state.canUseOnlineWrites
                  ? null
                  : () => _download(context),
              icon: controller.isDownloading
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.system_update_alt),
              label: Text(label),
            ),
          ],
        );
      },
    );
  }
}
