import 'models.dart';

class CoherentRefreshBundle {
  const CoherentRefreshBundle(
      {required this.candidate, required this.envelope});

  final AuthoritativeStateCandidate candidate;
  final AuthoritativeBaselineEnvelope envelope;
}

class AuthoritativeBaselineEnvelope {
  const AuthoritativeBaselineEnvelope({
    required this.snapshot,
    required this.fingerprint,
    required this.revision,
    required this.evaluationDate,
    required this.discountPolicyDefaults,
  });

  final Map<String, dynamic> snapshot;
  final String fingerprint;
  final int revision;
  final String evaluationDate;
  final Map<String, String> discountPolicyDefaults;
}

class AuthoritativeStateCandidate {
  const AuthoritativeStateCandidate({
    required this.user,
    required this.summary,
    required this.cardPaymentStatus,
    required this.judgment,
    required this.monthCloseStatus,
    required this.settings,
    required this.ownerDiscountMonth,
    required this.familyDiscountMonth,
    required this.transitDiscountProfile,
    required this.entries,
    required this.confirmedPlannedEntries,
    required this.panels,
    required this.cashFlows,
  });

  final AuthUser user;
  final Summary summary;
  final CardPaymentStatus cardPaymentStatus;
  final JudgmentState judgment;
  final MonthCloseStatus monthCloseStatus;
  final AppSettings settings;
  final CardDiscountMonth ownerDiscountMonth;
  final CardDiscountMonth familyDiscountMonth;
  final TransitDiscountProfileStatus transitDiscountProfile;
  final List<LedgerEntry> entries;
  final List<LedgerEntry> confirmedPlannedEntries;
  final List<MonthlyPanel> panels;
  final List<CashFlow> cashFlows;
}
