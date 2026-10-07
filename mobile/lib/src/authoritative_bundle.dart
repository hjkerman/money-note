import 'dart:convert';

import 'authoritative_bundle_validation.dart';
import 'authoritative_snapshot_validation.dart';
import 'coherent_refresh_models.dart';
import 'models.dart';
import 'money.dart';

typedef BundleStageObserver = void Function(String stage, Duration elapsed);

T _stage<T>(String name, BundleStageObserver? observer, T Function() build) {
  final watch = observer == null ? null : (Stopwatch()..start());
  final value = build();
  if (watch != null) observer!(name, watch.elapsed);
  return value;
}

/// Bundle-v1 parser only. It neither installs state nor publishes a baseline.
/// Server calculations remain authoritative; validation never repairs fields.
class AuthoritativeBundle {
  AuthoritativeBundle._(this.wire);
  final Map<String, dynamic> wire;

  factory AuthoritativeBundle.decode(List<int> bytes,
      {BundleStageObserver? onStage}) {
    final text = _stage('utf8', onStage, () => utf8.decode(bytes));
    _stage('raw_money', onStage, () => validateBundleRawMoney(text));
    final decoded = _stage('json_decode', onStage, () => jsonDecode(text));
    if (decoded is! Map<String, dynamic>) invalidBundle('root');
    return AuthoritativeBundle._fromDecoded(decoded, onStage: onStage);
  }

  // Do not expose an already-decoded entry point that can bypass raw-token
  // exactness checks after a JSON number has already rounded/underflowed.
  factory AuthoritativeBundle._fromDecoded(Map<String, dynamic> wire,
      {BundleStageObserver? onStage}) {
    _stage('presence_types', onStage, () => validateBundleShape(wire));
    _stage('money', onStage, () => validateMoneyPayload(wire));
    _stage('snapshot_authority_relationships', onStage,
        () => validateAuthoritativeSnapshot(wire));
    return AuthoritativeBundle._(
        _stage('freeze', onStage, () => _freeze(wire) as Map<String, dynamic>));
  }

  CoherentRefreshBundle toCoherentBundle(AuthUser user,
      {BundleStageObserver? onStage}) {
    if (wire['principal']['user_id'] != user.id) invalidBundle('principal');
    final s = wire['state'] as Map<String, dynamic>;
    final a = wire['authority'] as Map<String, dynamic>;
    final typed = _stage(
        'typed_models',
        onStage,
        () => (
              summary: Summary.fromJson(s['summary']),
              payment: CardPaymentStatus.fromJson(s['card_payment_status']),
              judgment: JudgmentState.fromJson(s['judgment']),
              status: MonthCloseStatus.fromJson(s['month_close_status']),
              settings: AppSettings.fromJson(s['settings']),
              owner: CardDiscountMonth.fromJson(s['owner_discount_month']),
              family: CardDiscountMonth.fromJson(s['family_discount_month']),
              transit: TransitDiscountProfileStatus.fromJson(
                  s['transit_discount_profile']),
              entries: _rows(s['entries'], LedgerEntry.fromJson),
              confirmed:
                  _rows(s['confirmed_planned_entries'], LedgerEntry.fromJson),
              panels: _rows(s['panels'], MonthlyPanel.fromJson),
              cash: _rows(s['cash_flows'], CashFlow.fromJson),
            ));
    return _stage(
        'candidate',
        onStage,
        () => CoherentRefreshBundle(
              candidate: AuthoritativeStateCandidate(
                  user: user,
                  summary: typed.summary,
                  cardPaymentStatus: typed.payment,
                  judgment: typed.judgment,
                  monthCloseStatus: typed.status,
                  settings: typed.settings,
                  ownerDiscountMonth: typed.owner,
                  familyDiscountMonth: typed.family,
                  transitDiscountProfile: typed.transit,
                  entries: typed.entries,
                  confirmedPlannedEntries: typed.confirmed,
                  panels: typed.panels,
                  cashFlows: typed.cash),
              envelope: AuthoritativeBaselineEnvelope(
                  snapshot: wire['snapshot'],
                  fingerprint: a['state_fingerprint'],
                  revision: a['state_revision'],
                  evaluationDate: a['evaluation_date'],
                  discountPolicyDefaults: Map<String, String>.unmodifiable(
                      Map<String, String>.from(a['discount_policy_defaults']))),
            ));
  }
}

List<T> _rows<T>(List rows, T Function(Map<String, dynamic>) parse) =>
    List<T>.unmodifiable(rows.map((row) => parse(row as Map<String, dynamic>)));

Object? _freeze(Object? value) {
  if (value is Map<String, dynamic>) {
    return Map<String, dynamic>.unmodifiable(
        value.map((key, v) => MapEntry(key, _freeze(v))));
  }
  if (value is List) return List<Object?>.unmodifiable(value.map(_freeze));
  return value;
}
