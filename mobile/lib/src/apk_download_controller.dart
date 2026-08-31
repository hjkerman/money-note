import 'package:flutter/foundation.dart';

import 'api_client.dart';
import 'apk_download_service.dart';
import 'apk_install_bridge.dart';

typedef ApkDownloadRunner = Future<void> Function(
  MoneyNoteApiClient api, {
  void Function(double? progress)? onProgress,
});
typedef InstalledVersionReader = Future<InstalledAppVersion?> Function();

class ApkDownloadController extends ChangeNotifier {
  ApkDownloadController({
    ApkDownloadRunner? downloadRunner,
    InstalledVersionReader? installedVersionReader,
  })  : _downloadRunner =
            downloadRunner ?? ApkDownloadService().downloadAndInstall,
        _installedVersionReader =
            installedVersionReader ?? ApkInstallBridge().installedVersion;

  final ApkDownloadRunner _downloadRunner;
  final InstalledVersionReader _installedVersionReader;

  InstalledAppVersion? installedVersion;
  bool isDownloading = false;
  double? progress;
  bool _disposed = false;

  Future<void> initialize() async {
    final version = await _installedVersionReader();
    if (_disposed) return;
    installedVersion = version;
    notifyListeners();
  }

  Future<void> download(MoneyNoteApiClient api) async {
    if (isDownloading) return;
    isDownloading = true;
    progress = null;
    notifyListeners();
    try {
      await _downloadRunner(
        api,
        onProgress: (value) {
          if (_disposed) return;
          progress = value;
          notifyListeners();
        },
      );
    } finally {
      if (!_disposed) {
        isDownloading = false;
        progress = null;
        notifyListeners();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
