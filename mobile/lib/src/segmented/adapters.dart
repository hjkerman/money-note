// Explicit isolated E4 adapters/workspace. Never registered by normal startup.
import 'dart:convert';
import 'dart:io';

import '../authoritative_bundle.dart';
import '../authoritative_bundle_validation.dart';
import '../coherent_refresh_models.dart';
import '../models.dart';
import '../offline/offline_data.dart';
import '../offline/offline_lineage_validator.dart';
import '../offline/offline_projection.dart';
import '../offline/offline_store.dart';
import '../offline/online_write_state.dart';
import 'c1.dart';
import 'protocol.dart';
import 'object.dart' show segmentedTables;
import 'store.dart';

part 'workspace.dart';

// §31 has no implemented verified recovery contract. There is deliberately no
// developer flag, boolean setter, synthetic capability or fabricated R1 proof.
Never requireSegmentedOfflineRecovery() =>
    rejectSegment('R1_RECOVERY_CONTRACT_REQUIRED');

class SegmentedAuthority {
  SegmentedAuthority._(this.generationId, this.sequence, this.target,
      this.candidate, this.discountPolicyDefaults, this.completeStoreHandle);
  final String generationId;
  final int sequence;
  final SyncTarget target;
  final AuthoritativeStateCandidate candidate;
  final Map<String, String> discountPolicyDefaults;
  final CompleteStoreHandle completeStoreHandle;
  // No snapshot/fingerprint field. This is NOT AuthoritativeBaselineEnvelope.
}

SegmentedAuthority readSegmentedAuthority(
    AcceptedReadView read, AuthUser user) {
  if (user.id != read.target.principalId) {
    rejectSegment('READ_PRINCIPAL_MISMATCH');
  }
  final s = read.hot['state'] as Map<String, dynamic>;
  final defaults = Map<String, String>.unmodifiable(
      Map<String, String>.from(read.control['discount_policy_defaults']));
  List<T> rows<T>(String key, T Function(Map<String, dynamic>) parse) =>
      List<T>.unmodifiable(
          (s[key] as List).map((row) => parse(row as Map<String, dynamic>)));
  return SegmentedAuthority._(
      read.generation.id!,
      read.generation.sequence,
      read.target,
      AuthoritativeStateCandidate(
          user: user,
          summary: Summary.fromJson(s['summary']),
          cardPaymentStatus:
              CardPaymentStatus.fromJson(s['card_payment_status']),
          judgment: JudgmentState.fromJson(s['judgment']),
          monthCloseStatus: MonthCloseStatus.fromJson(s['month_close_status']),
          settings: AppSettings.fromJson(s['settings']),
          ownerDiscountMonth:
              CardDiscountMonth.fromJson(s['owner_discount_month']),
          familyDiscountMonth:
              CardDiscountMonth.fromJson(s['family_discount_month']),
          transitDiscountProfile: TransitDiscountProfileStatus.fromJson(
              s['transit_discount_profile']),
          entries: rows('entries', LedgerEntry.fromJson),
          confirmedPlannedEntries:
              rows('confirmed_planned_entries', LedgerEntry.fromJson),
          panels: rows('panels', MonthlyPanel.fromJson),
          cashFlows: rows('cash_flows', CashFlow.fromJson)),
      defaults,
      read.completeStoreHandle);
}

const _exportOrder = <String, List<String>>{
  'ledger_entries': [
    'book_section',
    'entry_kind',
    'entry_date',
    'sort_order',
    'id'
  ],
  'monthly_panels': ['month', 'panel_type', 'sort_order', 'id'],
  'cash_flows': ['occurred_on', 'sort_order', 'id'],
  'card_payment_batches': ['id'],
  'card_payment_batch_items': ['batch_id', 'id'],
  'card_payment_events': ['event_date', 'id'],
  'card_payment_allocations': ['payment_event_id', 'id'],
  'card_payment_deferrals': ['target_payment_month', 'entry_payment_key'],
  'notification_candidate_registrations': ['registration_key'],
  'app_settings': ['key'],
  'app_labels': ['key']
};

int _sqliteAscending(Object? a, Object? b) {
  if (a == null) return b == null ? 0 : -1;
  if (b == null) return 1;
  if (a is num && b is num) return a.compareTo(b);
  if (a is String && b is String) {
    return scalarCompare(a, b); // SQLite BINARY UTF-8
  }
  rejectSegment('LEGACY_ORDER_INVALID');
}

// §22 explicit complete export boundary, never a normal hot refresh. Uses the
// original accepted control, existing flat-hash algorithm and existing strict
// full Bundle admission. No sync_root substitution or partial Snapshot.
CoherentRefreshBundle materializeLegacyRead(
    AcceptedReadView read, AuthUser user,
    {int maxBytes = 26214400}) {
  if (user.id != read.target.principalId) {
    rejectSegment('READ_PRINCIPAL_MISMATCH');
  }
  if (!read.hasFullMaterializationProof) {
    rejectSegment('MATERIALIZATION_PROOF_REQUIRED');
  }
  if (maxBytes <= 0) rejectSegment('LEGACY_MATERIALIZATION_BUDGET');
  final control = read.control,
      data = read.materializationRows(maxBytes: maxBytes);
  for (final table in segmentedTables) {
    (data[table] as List<Map<String, dynamic>>).sort((a, b) {
      for (final key in _exportOrder[table]!) {
        final order = _sqliteAscending(a[key], b[key]);
        if (order != 0) return order;
      }
      return 0;
    });
  }
  final metadata = <String, dynamic>{
    'schema_version': control['snapshot_schema'],
    'recurring_ownership_version': control['recurring_ownership_version'],
    'exported_at': control['exported_at'],
    'range': control['range']
  };
  final content = <String, dynamic>{
    ...metadata,
    'card_charge_policy': control['card_charge_policy'],
    'data': data
  };
  final contentHash = bundleHash(content);
  final snapshot = <String, dynamic>{
    ...content,
    'manifest': {
      'algorithm': 'sha256',
      'tables': {
        for (final table in segmentedTables)
          table: {
            'columns': control['columns'][table],
            'row_count': (data[table] as List).length,
            'sha256': bundleHash(data[table])
          }
      },
      'data_sha256': bundleHash(data),
      'card_charge_policy_sha256': bundleHash(control['card_charge_policy']),
      'content_sha256': contentHash
    },
    'snapshot_id': contentHash
  };
  final wire = <String, dynamic>{
    'bundle_version': 1,
    'principal': {'user_id': user.id},
    'authority': {
      'state_revision': int.parse(read.target.revision),
      'evaluation_date': read.target.context.date,
      'state_fingerprint': bundleHash({
        'schema_version': metadata['schema_version'],
        'range': metadata['range'],
        'card_charge_policy': control['card_charge_policy'],
        'data': data
      }),
      'discount_policy_defaults': control['discount_policy_defaults']
    },
    'state': read.hot['state'],
    'snapshot': snapshot
  };
  final bytes = utf8.encode(jsonEncode(wire));
  if (maxBytes <= 0 || bytes.length > maxBytes) {
    rejectSegment('LEGACY_MATERIALIZATION_BUDGET');
  }
  return AuthoritativeBundle.decode(bytes).toCoherentBundle(user);
}

// Two distinct views, never Apply(new segmented G, old J). Pending presentation
// remains the existing frozen OfflineProjection(B,J), with its original lineage.
// This snapshot does not acknowledge/retire/rebase anything and does not confer
// Offline entry authority. AppState guards its use after asynchronous reads.
class PendingLegacyView {
  PendingLegacyView._(this.lineage, this.bundle, this.projection);
  final String lineage;
  final OfflineReconciliationBundle bundle;
  final OfflineProjection? projection; // resolved J is NEVER projected again
}

Future<PendingLegacyView?> readPendingLegacyView(
    OfflineStore store, int owner) async {
  final initial = await store.loadMetadata();
  if (initial.mode == ConnectivityMode.online) {
    // ONLINE has no frozen B/J lineage. Do not read/hash the full legacy B just
    // to show an online marker, or manufacture a frozen view from that B.
    if ((await store.loadJournal()).isNotEmpty) {
      rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
    }
    return null;
  }
  if (initial.mode != ConnectivityMode.offline &&
      initial.mode != ConnectivityMode.reconciliationRequired) {
    // Finalizing requires the existing artifact/status/cleanup owner; this
    // read-only adapter cannot attach old J to the resolved new baseline.
    rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
  }
  final bundle = await store.loadReconciliationBundle();
  if (bundle == null || bundle.metadata.mode != initial.mode) {
    rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
  }
  if (bundle.baseline.user.id != owner) {
    rejectSegment('READ_PRINCIPAL_MISMATCH');
  }
  final lineage = store.recoveryLineageFingerprint(bundle.baseline);
  final resolved = bundle.metadata.reconciliationId != null &&
      bundle.baseline.resolvedReconciliationId ==
          bundle.metadata.reconciliationId;
  if (bundle.metadata.mode == ConnectivityMode.persistenceRecoveryBlocked ||
      !isConsistentPersistedLineage(
          metadata: bundle.metadata,
          baseline: bundle.baseline,
          resolved: resolved,
          journalIsEmpty: bundle.operations.isEmpty,
          baselineFingerprint: lineage)) {
    rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
  }
  return PendingLegacyView._(
      bundle.metadata.baselineLineageFingerprint!,
      bundle,
      resolved
          ? null
          : OfflineProjection.from(bundle.baseline, bundle.operations));
}

class SegmentedAdapterRead {
  const SegmentedAdapterRead(
      this.segmented, this.pendingLegacy, this.legacy, this.pendingOnlineWrite);
  final SegmentedAuthority segmented;
  final PendingLegacyView? pendingLegacy;
  final CoherentRefreshBundle? legacy; // explicit complete export only
  final PendingOnlineWrite? pendingOnlineWrite; // status, never acknowledgment
}
