/// Automatic recovery never replays a mutation. A confirmed server commit is
/// retired only after a fresh authoritative baseline is durably published.
/// An unknown outcome needs proof through its existing retry identity instead.
enum OnlineWriteStatus { outcomeUnknown, serverCommittedRebuildPending }

class PendingOnlineWrite {
  const PendingOnlineWrite(this.userId, this.token, this.status,
      {this.retryIdentity});
  final int userId;
  final String token;
  final OnlineWriteStatus status;
  final String? retryIdentity;

  PendingOnlineWrite committed() => PendingOnlineWrite(
      userId, token, OnlineWriteStatus.serverCommittedRebuildPending,
      retryIdentity: retryIdentity);

  Map<String, dynamic> toJson() => {
        'schema_version': 1,
        'user_id': userId,
        'token': token,
        'status': status.name,
        if (retryIdentity != null) 'retry_identity': retryIdentity,
      };

  factory PendingOnlineWrite.fromJson(Map<String, dynamic> json, int userId) {
    final token = json['token'];
    final status = json['status'];
    final retryIdentity = json['retry_identity'];
    if (json['schema_version'] != 1 ||
        json['user_id'] != userId ||
        token is! String ||
        token.isEmpty ||
        (retryIdentity != null &&
            (retryIdentity is! String || retryIdentity.isEmpty)) ||
        !OnlineWriteStatus.values.any((value) => value.name == status)) {
      throw const FormatException('invalid online write safety marker');
    }
    return PendingOnlineWrite(userId, token,
        OnlineWriteStatus.values.firstWhere((value) => value.name == status),
        retryIdentity: retryIdentity as String?);
  }
}
