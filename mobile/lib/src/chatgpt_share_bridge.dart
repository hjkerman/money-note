import 'package:flutter/services.dart';

class ChatGptShareBridge {
  static const _channel = MethodChannel('money_note/chatgpt_share');

  Future<void> shareAudit({
    required String filename,
    required String markdown,
  }) async {
    try {
      await _channel.invokeMethod<bool>('shareAudit', {
        'filename': filename,
        'markdown': markdown,
      });
    } on PlatformException catch (error) {
      if (error.code == 'chatgpt_not_installed') {
        throw const ChatGptShareException('ChatGPT 앱이 설치되어 있지 않습니다.');
      }
      throw ChatGptShareException(error.message ?? 'ChatGPT 앱을 열 수 없습니다.');
    } on MissingPluginException {
      throw const ChatGptShareException('이 기기에서는 ChatGPT 공유를 사용할 수 없습니다.');
    }
  }
}

class ChatGptShareException implements Exception {
  const ChatGptShareException(this.message);

  final String message;

  @override
  String toString() => message;
}
