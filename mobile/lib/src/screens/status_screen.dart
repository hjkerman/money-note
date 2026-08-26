import 'package:flutter/material.dart';

import '../app_state.dart';
import '../apk_download_service.dart';
import '../apk_install_bridge.dart';
import '../formatters.dart';
import '../theme.dart';
import '../widgets/money_card.dart';
import 'management_screen.dart';

class StatusScreen extends StatelessWidget {
  const StatusScreen({required this.state, super.key});

  final AppState state;

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
                onPressed: state.isBusy ? null : state.logout,
                icon: const Icon(Icons.logout),
                tooltip: '로그아웃'),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
                child:
                    AmountTile(label: '카드대금', amount: won(summary?.cardTotal))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(
                    label: '월 지출', amount: won(summary?.currentSpendingTotal))),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
                child: AmountTile(
                    label: '잔여 유동성', amount: won(summary?.remainingLiquidity))),
            const SizedBox(width: 12),
            Expanded(
                child: AmountTile(
                    label: '동결', amount: won(summary?.frozenAssetTotal))),
          ],
        ),
        const SectionTitle('관리'),
        ManagementMenuList(state: state),
        if (state.statusMessage.isNotEmpty) ...[
          const SizedBox(height: 14),
          Text(state.statusMessage, style: const TextStyle(color: moneyMuted)),
        ],
        const SizedBox(height: 24),
        _ApkDownloadButton(state: state),
      ],
    );
  }
}

class _ApkDownloadButton extends StatefulWidget {
  const _ApkDownloadButton({required this.state});

  final AppState state;

  @override
  State<_ApkDownloadButton> createState() => _ApkDownloadButtonState();
}

class _ApkDownloadButtonState extends State<_ApkDownloadButton> {
  final ApkDownloadService _service = ApkDownloadService();
  final ApkInstallBridge _installBridge = ApkInstallBridge();
  InstalledAppVersion? _installedVersion;
  bool _downloading = false;
  double? _progress;

  @override
  void initState() {
    super.initState();
    _loadInstalledVersion();
  }

  Future<void> _loadInstalledVersion() async {
    final version = await _installBridge.installedVersion();
    if (mounted) setState(() => _installedVersion = version);
  }

  Future<void> _download() async {
    if (_downloading) return;
    setState(() {
      _downloading = true;
      _progress = null;
    });
    try {
      await _service.downloadAndInstall(
        widget.state.api,
        onProgress: (progress) {
          if (mounted) setState(() => _progress = progress);
        },
      );
    } on ApkDownloadException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) {
        setState(() {
          _downloading = false;
          _progress = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final progress = _progress;
    final label = !_downloading
        ? 'APK 다운로드'
        : progress == null
            ? 'APK 받는 중...'
            : 'APK 받는 중 ${(progress * 100).round()}%';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_installedVersion case final version?) ...[
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
          onPressed: _downloading ? null : _download,
          icon: _downloading
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.system_update_alt),
          label: Text(label),
        ),
      ],
    );
  }
}
