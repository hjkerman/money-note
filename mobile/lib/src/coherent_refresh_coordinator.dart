import 'api_client.dart';
import 'models.dart';

class RefreshTicket {
  const RefreshTicket(this.lineageGeneration, this.authenticationGeneration,
      this.requestGeneration);

  final int lineageGeneration;
  final int authenticationGeneration;
  final int requestGeneration;
}

class CoherentRefreshCoordinator {
  CoherentRefreshCoordinator(this.api,
      {required String Function() localToday,
      required String Function(DateTime) formatDate})
      : _localToday = localToday,
        _formatDate = formatDate;

  final MoneyNoteApiClient api;
  final String Function() _localToday;
  final String Function(DateTime) _formatDate;
  int _requestGeneration = 0;

  RefreshTicket begin(int lineageGeneration, int authenticationGeneration) =>
      RefreshTicket(
          lineageGeneration, authenticationGeneration, ++_requestGeneration);

  void invalidateAuthentication() => _requestGeneration += 1;

  bool mayInstall(RefreshTicket ticket,
          {required int currentLineageGeneration,
          required int currentAuthenticationGeneration,
          required bool modeAllowed}) =>
      ticket.lineageGeneration == currentLineageGeneration &&
      ticket.authenticationGeneration == currentAuthenticationGeneration &&
      ticket.requestGeneration == _requestGeneration &&
      modeAllowed;

  Future<CoherentRefreshBundle> acquire(
      AuthUser? Function() currentUser) async {
    for (var attempt = 0; attempt < 3; attempt += 1) {
      final before = await _readAuthoritativeBaselineEnvelope();
      final candidate = await _fetchAuthoritativeStateCandidate(currentUser());
      final after = await _readAuthoritativeBaselineEnvelope();
      if (before.fingerprint != after.fingerprint ||
          before.revision != after.revision ||
          before.evaluationDate != after.evaluationDate ||
          candidate.monthCloseStatus.calendarDate != after.evaluationDate) {
        continue;
      }
      return CoherentRefreshBundle(candidate: candidate, envelope: after);
    }
    throw MoneyNoteApiException(
      '동기화 중 서버 데이터가 계속 변경되어 coherent offline baseline을 만들지 못했습니다.',
    );
  }

  Future<AuthoritativeStateCandidate> _fetchAuthoritativeStateCandidate(
      AuthUser? currentUser) async {
    if (currentUser == null) {
      throw MoneyNoteApiException('로그인 사용자 정보가 없습니다.');
    }
    // acquire() brackets this entire graph with the same two baseline fences.
    // Cash needs status's server date; policy month selection still uses status
    // plus entries/panels (including the existing historical fallback).
    final statusFuture = api.monthCloseStatus();
    final entriesFuture = api.currentEntries();
    final panelsFuture = api.currentPanels();
    final summaryFuture = api.summary();
    final paymentFuture = api.currentCardPaymentStatus();
    final judgmentFuture = api.judgment();
    final confirmedFuture = api.confirmedPlannedEntries();
    final settingsFuture = api.settings();
    final cashFuture = statusFuture.then(_loadRecentCashFlows);
    // Keep policy reads out of the heavy core phase: wider overlap regressed
    // large-history tails. Cash is independent of policy month selection and
    // may still overlap the policy phase. No read moves outside the fences.
    final coreReadsFuture = Future.wait([
      summaryFuture,
      paymentFuture,
      judgmentFuture,
      entriesFuture,
      confirmedFuture,
      panelsFuture,
      settingsFuture,
    ]);
    final discountsFuture = Future.wait([
      statusFuture,
      entriesFuture,
      panelsFuture,
      coreReadsFuture,
    ]).then((monthInputs) {
      final freshMonth = _monthFor(
        monthInputs[0] as MonthCloseStatus,
        monthInputs[1] as List<LedgerEntry>,
        monthInputs[2] as List<MonthlyPanel>,
      );
      return Future.wait([
        api.discountMonth(freshMonth, 'owner'),
        api.discountMonth(freshMonth, 'family'),
        api.transitDiscountProfile(freshMonth),
      ]);
    });
    final results = await Future.wait([
      summaryFuture,
      paymentFuture,
      judgmentFuture,
      entriesFuture,
      confirmedFuture,
      panelsFuture,
      cashFuture,
      settingsFuture,
      statusFuture,
      discountsFuture,
    ]);
    final freshSummary = results[0] as Summary;
    final freshCardPaymentStatus = results[1] as CardPaymentStatus;
    final freshJudgment = results[2] as JudgmentState;
    final freshEntries = results[3] as List<LedgerEntry>;
    final freshConfirmedPlannedEntries = results[4] as List<LedgerEntry>;
    final freshPanels = results[5] as List<MonthlyPanel>;
    final freshCashFlows = results[6] as List<CashFlow>;
    final freshSettings = results[7] as AppSettings;
    final freshMonthCloseStatus = results[8] as MonthCloseStatus;
    final discountResults = results[9] as List<Object>;

    return AuthoritativeStateCandidate(
      user: currentUser,
      summary: freshSummary,
      cardPaymentStatus: freshCardPaymentStatus,
      judgment: freshJudgment,
      entries: List.unmodifiable(freshEntries),
      confirmedPlannedEntries: List.unmodifiable(freshConfirmedPlannedEntries),
      panels: List.unmodifiable(freshPanels),
      cashFlows: List.unmodifiable(freshCashFlows),
      settings: freshSettings,
      monthCloseStatus: freshMonthCloseStatus,
      ownerDiscountMonth: discountResults[0] as CardDiscountMonth,
      familyDiscountMonth: discountResults[1] as CardDiscountMonth,
      transitDiscountProfile:
          discountResults[2] as TransitDiscountProfileStatus,
    );
  }

  Future<AuthoritativeBaselineEnvelope>
      _readAuthoritativeBaselineEnvelope() async {
    final authoritative = await api.offlineReconciliationBaseline();
    final snapshot = authoritative['snapshot'];
    final fingerprint = authoritative['state_fingerprint'];
    final revision = authoritative['state_revision'];
    final evaluationDate = authoritative['evaluation_date'];
    final rawDefaults = authoritative['discount_policy_defaults'];
    if (snapshot is! Map<String, dynamic> ||
        fingerprint is! String ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(fingerprint) ||
        revision is! int ||
        revision < 0 ||
        evaluationDate is! String ||
        DateTime.tryParse(evaluationDate) == null ||
        rawDefaults is! Map ||
        !{'enabled', 'disabled'}.contains(rawDefaults['owner']) ||
        !{'enabled', 'disabled'}.contains(rawDefaults['family'])) {
      throw MoneyNoteApiException('오프라인 기준 Snapshot 응답이 올바르지 않습니다.');
    }
    return AuthoritativeBaselineEnvelope(
      snapshot: Map<String, dynamic>.unmodifiable(snapshot),
      fingerprint: fingerprint,
      revision: revision,
      evaluationDate: evaluationDate,
      discountPolicyDefaults: Map<String, String>.from(rawDefaults),
    );
  }

  Future<List<CashFlow>> _loadRecentCashFlows(MonthCloseStatus status) {
    final serverDate = DateTime.tryParse(status.calendarDate);
    if (serverDate == null) {
      throw MoneyNoteApiException('서버 기준 날짜를 확인할 수 없습니다.');
    }
    final dateFrom = DateTime(serverDate.year, serverDate.month - 1, 1);
    final dateTo = DateTime(serverDate.year, serverDate.month + 1, 0);
    return api.cashFlows(
      dateFrom: _formatDate(dateFrom),
      dateTo: _formatDate(dateTo),
    );
  }

  String _monthFor(MonthCloseStatus status, List<LedgerEntry> freshEntries,
      List<MonthlyPanel> freshPanels) {
    if (status.calendarMonth.length >= 7) {
      return status.calendarMonth.substring(0, 7);
    }
    for (final entry in freshEntries.reversed) {
      final date = entry.entryDate;
      if (date != null && date.length >= 7) return date.substring(0, 7);
    }
    if (freshPanels.isNotEmpty) return freshPanels.last.month;
    return _localToday().substring(0, 7);
  }
}

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
