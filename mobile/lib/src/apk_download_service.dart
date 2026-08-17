import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'api_client.dart';
import 'apk_install_bridge.dart';

class ApkDownloadService {
  ApkDownloadService({ApkInstallBridge? installBridge})
      : _installBridge = installBridge ?? ApkInstallBridge();

  static const int _maximumApkBytes = 200 * 1024 * 1024;
  final ApkInstallBridge _installBridge;

  Future<void> downloadAndInstall(
    MoneyNoteApiClient api, {
    void Function(double? progress)? onProgress,
  }) async {
    if (!await _installBridge.canInstallPackages()) {
      await _installBridge.openInstallSettings();
      throw const ApkDownloadException(
        '이 출처의 앱 설치를 허용한 뒤 APK 다운로드를 다시 눌러주세요.',
      );
    }

    final root = await getTemporaryDirectory();
    final directory = Directory('${root.path}/apk-updates');
    await _clearDirectory(directory);
    await directory.create(recursive: true);
    final partial = File('${directory.path}/money-note.apk.part');
    final completed = File('${directory.path}/money-note.apk');

    try {
      final download = await api.openApkDownload();
      final expectedBytes = download.contentLength;
      if (expectedBytes != null && expectedBytes > _maximumApkBytes) {
        throw const ApkDownloadException('APK 파일 크기가 안전 한도를 초과했습니다.');
      }

      var receivedBytes = 0;
      final sink = partial.openWrite();
      try {
        await for (final chunk in download.bytes) {
          receivedBytes += chunk.length;
          if (receivedBytes > _maximumApkBytes) {
            throw const ApkDownloadException('APK 파일 크기가 안전 한도를 초과했습니다.');
          }
          sink.add(chunk);
          onProgress?.call(
            expectedBytes == null || expectedBytes <= 0
                ? null
                : (receivedBytes / expectedBytes).clamp(0, 1),
          );
        }
        await sink.flush();
      } finally {
        await sink.close();
      }

      if (receivedBytes == 0 ||
          (expectedBytes != null && receivedBytes != expectedBytes)) {
        throw const ApkDownloadException('APK 다운로드가 완전하지 않습니다.');
      }
      await partial.rename(completed.path);
      await _installBridge.installApk(completed.path);
    } catch (error) {
      await _deleteIfPresent(partial);
      await _deleteIfPresent(completed);
      if (error is ApkDownloadException) rethrow;
      if (error is ApkInstallException) {
        throw ApkDownloadException(error.message);
      }
      if (error is MoneyNoteApiException) {
        throw ApkDownloadException(error.message);
      }
      throw const ApkDownloadException('APK를 내려받지 못했습니다.');
    }
  }

  Future<void> _clearDirectory(Directory directory) async {
    if (!await directory.exists()) return;
    await for (final entity in directory.list()) {
      await entity.delete(recursive: true);
    }
  }

  Future<void> _deleteIfPresent(File file) async {
    if (await file.exists()) await file.delete();
  }
}

class ApkDownloadException implements Exception {
  const ApkDownloadException(this.message);

  final String message;

  @override
  String toString() => message;
}
