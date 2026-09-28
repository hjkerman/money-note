import 'offline_data.dart';

/// Persisted B/J/metadata combinations accepted at restart. This function
/// neither reads storage nor changes the reconciliation state machine.
bool isConsistentPersistedLineage({
  required OfflineWorkspaceMetadata metadata,
  required OfflineBaseline? baseline,
  required bool resolved,
  required bool journalIsEmpty,
  required String? baselineFingerprint,
}) {
  final mode = metadata.mode;
  final phase = metadata.phase;
  final choice = metadata.reconciliationChoice;
  final id = metadata.reconciliationId;
  final commit = metadata.serverCommitStatus;
  final hasChoiceAndId = choice != null && id != null && id.isNotEmpty;
  final noChoiceOrId = choice == null && id == null;
  final hasServerArtifact = metadata.serverArtifactFilename != null;
  final anyMobileArtifact = metadata.mobileArtifactFilename != null ||
      metadata.mobileArtifactSha256 != null;
  final hasMobileArtifact = metadata.mobileArtifactFilename != null &&
      metadata.mobileArtifactSha256 != null;
  if (mode == ConnectivityMode.persistenceRecoveryBlocked) return true;
  if (mode == ConnectivityMode.online) {
    return journalIsEmpty &&
        noChoiceOrId &&
        phase == ReconciliationPhase.none &&
        commit == ServerCommitStatus.none &&
        metadata.baselineLineageFingerprint == null &&
        !hasServerArtifact &&
        !anyMobileArtifact &&
        metadata.currentServerFingerprint == null &&
        !metadata.serverChanged &&
        !metadata.confirmServerChanged;
  }
  if (baseline == null ||
      metadata.baselineLineageFingerprint == null ||
      (!resolved &&
          metadata.baselineLineageFingerprint != baselineFingerprint) ||
      (baseline.resolvedReconciliationId != null &&
          mode == ConnectivityMode.reconciliationFinalizing &&
          !resolved)) {
    return false;
  }
  if (mode == ConnectivityMode.offline) {
    return noChoiceOrId &&
        phase == ReconciliationPhase.none &&
        commit == ServerCommitStatus.none &&
        !hasServerArtifact &&
        !anyMobileArtifact &&
        metadata.currentServerFingerprint == null &&
        !metadata.serverChanged &&
        !metadata.confirmServerChanged;
  }
  if (mode == ConnectivityMode.reconciliationRequired) {
    if (commit != ServerCommitStatus.none || metadata.confirmServerChanged) {
      return false;
    }
    if (phase == ReconciliationPhase.none) {
      return noChoiceOrId &&
          !hasServerArtifact &&
          !anyMobileArtifact &&
          metadata.currentServerFingerprint == null &&
          !metadata.serverChanged;
    }
    if (!hasChoiceAndId || resolved) return false;
    if (phase == ReconciliationPhase.preparing) {
      return !anyMobileArtifact &&
          (!hasServerArtifact || metadata.currentServerFingerprint != null);
    }
    return phase == ReconciliationPhase.ready &&
        hasServerArtifact &&
        hasMobileArtifact &&
        metadata.currentServerFingerprint != null &&
        !metadata.confirmServerChanged;
  }
  if (mode != ConnectivityMode.reconciliationFinalizing ||
      !hasChoiceAndId ||
      !hasServerArtifact ||
      !hasMobileArtifact ||
      metadata.currentServerFingerprint == null) {
    return false;
  }
  return switch (phase) {
    ReconciliationPhase.mobileRequestPending =>
      choice == ReconciliationChoice.applyToServer &&
          commit == ServerCommitStatus.unknown &&
          !resolved &&
          (!metadata.serverChanged || metadata.confirmServerChanged),
    ReconciliationPhase.mobileCommitted =>
      choice == ReconciliationChoice.applyToServer &&
          commit == ServerCommitStatus.committed &&
          (!metadata.serverChanged || metadata.confirmServerChanged),
    ReconciliationPhase.serverWinsFinalizing =>
      choice == ReconciliationChoice.discardAndUseServer &&
          commit == ServerCommitStatus.none &&
          !metadata.confirmServerChanged,
    _ => false,
  };
}
