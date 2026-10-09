import 'api_client.dart';
import 'models.dart';
import 'coherent_refresh_models.dart';
import 'authoritative_bundle.dart';

export 'coherent_refresh_models.dart';

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

  /// Acquisition never publishes, installs or retires pending state. AppState
  /// retains the guarded durable boundary after this returns.
  Future<CoherentRefreshBundle> acquire(
    AuthUser? Function() currentUser, {
    required RefreshTicket ticket,
    required int Function() currentLineageGeneration,
    required int Function() currentAuthenticationGeneration,
    required bool Function() modeAllowed,
  }) =>
      _acquireBundle(currentUser,
          ticket: ticket,
          currentLineageGeneration: currentLineageGeneration,
          currentAuthenticationGeneration: currentAuthenticationGeneration,
          modeAllowed: modeAllowed);

  /// Diagnostics share normal admission but do not publish or install state.
  Future<CoherentRefreshBundle> acquireBundleForDiagnostics(
    AuthUser? Function() currentUser, {
    required RefreshTicket ticket,
    required int Function() currentLineageGeneration,
    required int Function() currentAuthenticationGeneration,
    required bool Function() modeAllowed,
  }) =>
      _acquireBundle(currentUser,
          ticket: ticket,
          currentLineageGeneration: currentLineageGeneration,
          currentAuthenticationGeneration: currentAuthenticationGeneration,
          modeAllowed: modeAllowed);

  Future<CoherentRefreshBundle> _acquireBundle(
    AuthUser? Function() currentUser, {
    required RefreshTicket ticket,
    required int Function() currentLineageGeneration,
    required int Function() currentAuthenticationGeneration,
    required bool Function() modeAllowed,
  }) async {
    final selectedUser = currentUser();
    bool allowed() =>
        selectedUser != null &&
        currentUser()?.id == selectedUser.id &&
        mayInstall(ticket,
            currentLineageGeneration: currentLineageGeneration(),
            currentAuthenticationGeneration: currentAuthenticationGeneration(),
            modeAllowed: modeAllowed());
    void requireAuthority() {
      if (!allowed()) {
        throw MoneyNoteApiException('오래된 authoritative bundle 결과를 폐기했습니다.',
            code: 'stale_authoritative_bundle');
      }
    }

    requireAuthority();
    final bytes = await api.authoritativeStateBytes();
    requireAuthority();
    try {
      final result =
          AuthoritativeBundle.decode(bytes).toCoherentBundle(selectedUser!);
      requireAuthority();
      return result;
    } on FormatException {
      throw MoneyNoteApiException('Authoritative bundle 응답이 올바르지 않습니다.',
          code: 'invalid_authoritative_bundle');
    }
  }

  /// Explicit legacy regression oracle only; never a normal-runtime fallback.
  Future<CoherentRefreshBundle> acquireLegacyForDiagnostics(
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
    // The explicit legacy oracle brackets this graph with baseline fences.
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
