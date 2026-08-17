import 'package:flutter/services.dart';

class ApkInstallBridge {
  static const _channel = MethodChannel('money_note/apk_install');

  Future<bool> canInstallPackages() async {
    return await _channel.invokeMethod<bool>('canInstallPackages') ?? false;
  }

  Future<void> openInstallSettings() async {
    await _channel.invokeMethod<bool>('openInstallSettings');
  }

  Future<void> installApk(String path) async {
    try {
      await _channel.invokeMethod<bool>('installApk', {'path': path});
    } on PlatformException catch (error) {
      throw ApkInstallException(error.message ?? 'APK 설치 화면을 열 수 없습니다.');
    } on MissingPluginException {
      throw const ApkInstallException('이 기기에서는 APK 설치를 시작할 수 없습니다.');
    }
  }
}

class ApkInstallException implements Exception {
  const ApkInstallException(this.message);

  final String message;

  @override
  String toString() => message;
}
