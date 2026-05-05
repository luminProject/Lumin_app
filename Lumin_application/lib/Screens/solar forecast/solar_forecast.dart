// ══════════════════════════════════════════════════════════════════
//  solar_forecast.dart
//
//  Solar Forecast screen — displays the forecast state for the user's
//  solar system. State is determined by the backend and returned as a
//  `case` string. This file handles all UI rendering per case.
//
//  Cases:
//    no_panels          — user has no production device
//    collecting         — collecting data for current season
//    collecting_extended— collection spans two seasons (installed late)
//    forecast_available — previous season complete, forecast ready
//    feature_disabled   — device offline ≥ 15 days
// ══════════════════════════════════════════════════════════════════

import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/services/api_service.dart';
import 'package:lumin_application/Screens/devices/device_management_page.dart';


// ═══════════════════════════════════════════════════════════
//  GHI BASELINE DATA
//  Source: NREL PVWatts / Saudi meteorological stations
//  Used to compute the α (personalized performance factor)
//  and to project future season production in forecast_available.
//  Formula: E (kWh) = GHI × PR × P_nom × days  (IEC 61724-1)
// ═══════════════════════════════════════════════════════════

// Monthly average GHI (kWh/m²/day) — Saudi national average
const _kGhi = <int, double>{
  1: 4.14, 2: 5.01, 3: 6.02, 4: 6.71,  5: 7.14,
  6: 7.27, 7: 6.98, 8: 6.75, 9: 6.21, 10: 5.44,
  11: 4.52, 12: 3.89,
};

// Days per month (non-leap year)
const _kDays = <int, int>{
  1: 31, 2: 28, 3: 31, 4: 30,  5: 31,
  6: 30, 7: 31, 8: 31, 9: 30, 10: 31,
  11: 30, 12: 31,
};

// Performance Ratio per IEC 61724-1
const _kPR = 0.78;

/// Expected production for a given month and panel capacity.
double _eExpected(int month, double panelCapacity) {
  final ghi  = _kGhi[month]  ?? 6.0;
  final days = _kDays[month] ?? 30;
  return ghi * _kPR * panelCapacity * days;
}

/// Expected production with a 0.5%/year growth factor applied.
/// yearDelta = forecastYear - baseYear
double _eExpectedFuture(int month, double panelCapacity, int yearDelta) {
  final ghi  = (_kGhi[month] ?? 6.0) * (1 + 0.005 * yearDelta);
  final days = _kDays[month] ?? 30;
  return ghi * _kPR * panelCapacity * days;
}

/// Return the ordered list of month numbers for a given season name.
List<int> _seasonMonthNums(String season) {
  switch (season) {
    case 'winter': return [12, 1, 2];
    case 'spring': return [3, 4, 5];
    case 'summer': return [6, 7, 8];
    case 'autumn': return [9, 10, 11];
    default:       return [1, 2, 3];
  }
}


// ═══════════════════════════════════════════════════════════
//  PAGE
// ═══════════════════════════════════════════════════════════

class SolarForecastPage extends StatefulWidget {
  const SolarForecastPage({super.key});
  @override
  State<SolarForecastPage> createState() => _SolarForecastPageState();
}

class _SolarForecastPageState extends State<SolarForecastPage> {
  final _api    = ApiService();
  bool _loading = true;
  String? _error;
  Map<String, dynamic> _data = {};
  bool _hasFetched = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_hasFetched) { _hasFetched = true; _fetch(); }
  }

  Future<void> _fetch() async {
    setState(() { _loading = true; _error = null; });
    try {
      final result = await _api.getSolarForecast();
      setState(() { _data = result; _loading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  void _refresh() { _hasFetched = false; didChangeDependencies(); }

  @override
  Widget build(BuildContext context) => GradientBackground(
    child: ResponsiveLayout(
      showAppBar: true,
      title: 'Solar Forecast',
      bottomNavigationBar: const HomeBottomNav(currentIndex: 2),
      child: _loading
          ? const _LoadingState()
          : _error != null
              ? _ErrorState(error: _error!, onRetry: _fetch)
              : _buildCase(),
    ));

  /// Route to the correct case widget based on the backend response.
  Widget _buildCase() {
    switch (_data['case'] as String? ?? 'no_panels') {
      case 'no_panels':           return _NoPanelsCase(data: _data);
      case 'collecting':          return _CollectingCase(data: _data, onRefresh: _refresh);
      case 'collecting_extended': return _CollectingExtendedCase(data: _data, onRefresh: _refresh);
      case 'forecast_available':  return _ForecastAvailableCase(data: _data, onRefresh: _refresh);
      case 'feature_disabled':    return _FeatureDisabled(data: _data, onCheck: _handleCheckDevice);
      default:                    return _NoPanelsCase(data: _data);
    }
  }

  /// Handle the reconnect flow from the feature_disabled screen.
  Future<void> _handleCheckDevice() async {
    setState(() => _loading = true);
    try {
      final result      = await _api.checkSolarDevice();
      final reconnected = result['reconnected'] as bool? ?? false;
      if (reconnected) {
        await _fetch();
        if (_data['case'] == 'feature_disabled' && mounted) {
          Navigator.push(context,
            MaterialPageRoute(builder: (_) => const DeviceManagementPage()));
        }
      } else if (mounted) {
        Navigator.push(context,
          MaterialPageRoute(builder: (_) => const DeviceManagementPage()));
      }
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        Navigator.push(context,
          MaterialPageRoute(builder: (_) => const DeviceManagementPage()));
      }
    }
  }
}


// ═══════════════════════════════════════════════════════════
//  LOADING / ERROR
// ═══════════════════════════════════════════════════════════

class _LoadingState extends StatelessWidget {
  const _LoadingState();
  @override
  Widget build(BuildContext context) => const Center(
    child: CircularProgressIndicator(color: AppColors.mint));
}

class _ErrorState extends StatelessWidget {
  final String error; final VoidCallback onRetry;
  const _ErrorState({required this.error, required this.onRetry});
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(padding: const EdgeInsets.all(24),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.error_outline_rounded, color: Color(0xFFFF5A52), size: 40),
        const SizedBox(height: 12),
        const Text('Something went wrong',
          style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
        const SizedBox(height: 6),
        Text(error, style: const TextStyle(fontSize: 11, color: AppColors.sub),
          textAlign: TextAlign.center),
        const SizedBox(height: 18),
        ElevatedButton(onPressed: onRetry,
          style: ElevatedButton.styleFrom(backgroundColor: AppColors.button,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
          child: const Text('Retry', style: TextStyle(fontWeight: FontWeight.w900))),
      ])));
}


// ═══════════════════════════════════════════════════════════
//  CASE: no_panels
//  User has no production device — show regional GHI estimate.
// ═══════════════════════════════════════════════════════════

class _NoPanelsCase extends StatelessWidget {
  final Map<String, dynamic> data;
  const _NoPanelsCase({required this.data});
  static const _yellow = Color(0xFFFFC56B);

  @override
  Widget build(BuildContext context) {
    final city       = data['city'] as String? ?? '';
    final avgGhi     = (data['avg_daily_ghi'] as num? ?? 0.0).toDouble();
    final avgMonthly = (data['avg_monthly_production'] as num? ?? 0.0).toDouble();

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          if (city.isNotEmpty) _PillCity(city),
          const Spacer(),
          _InfoBtn(title: 'About Solar Forecast',
            body: 'Solar Forecast predicts your solar panel production for upcoming '
                  'seasons based on the GHI solar radiation model for your region.\n\n'
                  'Once you install solar panels and connect your system, we\'ll '
                  'collect your real production data each season and build personalized '
                  'forecasts just for you.'),
        ]),
        const SizedBox(height: 28),
        Center(child: Container(width: 80, height: 80,
          decoration: BoxDecoration(color: _yellow.withOpacity(0.12), shape: BoxShape.circle),
          child: const Icon(Icons.solar_power_rounded, color: _yellow, size: 38))),
        const SizedBox(height: 16),
        const Center(child: Text('Feature Requires Solar Panels',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800))),
        const SizedBox(height: 6),
        const Center(child: Padding(padding: EdgeInsets.symmetric(horizontal: 20),
          child: Text('Install a solar system and connect it to unlock personalized forecasts.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: AppColors.sub, height: 1.5)))),
        const SizedBox(height: 24),
        GlassCard(radius: 18, padding: const EdgeInsets.all(16), child: Column(
          crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _IconBox(icon: Icons.wb_sunny_rounded, color: _yellow),
              const SizedBox(width: 10),
              const Text('Solar Potential — Your Region',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: _yellow)),
            ]),
            const SizedBox(height: 14),
            _Row2(label: 'Avg daily solar radiation',
              value: '${avgGhi.toStringAsFixed(1)} kWh/m\u00b2/day'),
            const SizedBox(height: 8),
            _Row2(label: 'Est. monthly production (5 kWp)',
              value: '~${avgMonthly.toStringAsFixed(0)} kWh/mo'),
            const SizedBox(height: 12),
            const _NoteBox(icon: Icons.info_outline_rounded, color: _yellow,
              text: 'Estimates use a standard 5 kWp system with a Performance Ratio of 0.78. '
                    'Actual production varies by system size, panel type, and local conditions.'),
          ])),
        const SizedBox(height: 12),
        const _Disclaimer(noPanels: true),
      ]));
  }
}


// ═══════════════════════════════════════════════════════════
//  CASE: collecting
//  Device installed at the start of a season.
//  Collecting data normally through the current season.
// ═══════════════════════════════════════════════════════════

class _CollectingCase extends StatelessWidget {
  final Map<String, dynamic> data;
  final VoidCallback onRefresh;
  const _CollectingCase({required this.data, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    final city            = data['city']            as String? ?? '';
    final season          = data['season']           as String;
    final emoji           = data['season_emoji']     as String;
    final collectedDays   = (data['collected_days']  as num).toInt();
    final daysMissed      = (data['days_missed']     as num? ?? 0).toInt();
    final daysRemaining   = (data['days_remaining']  as num? ?? 0).toInt();
    final daysElapsed     = (data['days_elapsed']    as num? ?? collectedDays).toInt();
    final totalDays       = (data['total_days']      as num).toInt();
    final daysOffline     = (data['days_offline']    as num? ?? 0).toInt();
    final lastReadingDate = data['last_reading_date'] as String?;

    const totalWeeks   = 12;
    final elapsedWeeks = ((daysElapsed / totalDays) * totalWeeks).round().clamp(0, totalWeeks);
    final weeksLeft    = (daysRemaining / 7).round().clamp(0, 12);

    return RefreshIndicator(
      color: AppColors.mint,
      onRefresh: () async => onRefresh(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _PageHeader(city: city, season: season, emoji: emoji,
            infoTitle: 'How Forecasts Work',
            infoBody: 'We collect your real production data throughout each season.\n\n'
                      'Once a full season ends, we compare your output to GHI solar '
                      'radiation trends and predict how your system will perform in '
                      'the same season next year — tailored to your actual system.\n\n'
                      'One complete season is enough to generate your first personalized forecast.'),
          const SizedBox(height: 20),
          if (daysOffline > 0) ...[
            _DailyMissingWarning(daysOffline: daysOffline, lastReadingDate: lastReadingDate),
            const SizedBox(height: 12),
          ],
          GlassCard(radius: 18, padding: const EdgeInsets.all(16), child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
              const _CardHeader(icon: Icons.data_thresholding_outlined, color: AppColors.cyan,
                title: 'Collecting Season Data',
                subtitle: 'Your forecast will be ready once this season ends'),
              const SizedBox(height: 18),
              _SeasonTimeline(totalWeeks: totalWeeks, elapsedWeeks: elapsedWeeks,
                seasonStart: data['season_start'] as String? ?? ''),
              const SizedBox(height: 14),
              _StatsRow(collectedDays: collectedDays, daysMissed: daysMissed, daysRemaining: daysRemaining),
              const SizedBox(height: 14),
              _NoteBox(icon: Icons.schedule_rounded, color: AppColors.cyan,
                text: '$weeksLeft week${weeksLeft == 1 ? '' : 's'} remaining in '
                      '${_cap(season)}. Your personalized forecast will appear '
                      'once the season is complete.'),
            ])),
          const SizedBox(height: 12),
          const _Disclaimer(),
        ])));
  }
}


// ═══════════════════════════════════════════════════════════
//  CASE: collecting_extended
//  Device installed near the end of a season.
//  Collection extends into the next season to reach the
//  45-day minimum threshold for a reliable forecast.
// ═══════════════════════════════════════════════════════════

class _CollectingExtendedCase extends StatelessWidget {
  final Map<String, dynamic> data;
  final VoidCallback onRefresh;
  const _CollectingExtendedCase({required this.data, required this.onRefresh});

  /// Build an ordered list of month abbreviations from startIso to endIso.
  List<String> _monthRange(String startIso, String endIso) {
    const names = ['', 'Jan','Feb','Mar','Apr','May','Jun',
                   'Jul','Aug','Sep','Oct','Nov','Dec'];
    final s = DateTime.parse(startIso);
    final e = DateTime.parse(endIso);
    final result = <String>[];
    var cur = DateTime(s.year, s.month);
    while (!cur.isAfter(DateTime(e.year, e.month))) {
      result.add(names[cur.month]);
      cur = DateTime(cur.year, cur.month + 1);
    }
    return result;
  }

  @override
  Widget build(BuildContext context) {
    final city            = data['city']              as String? ?? '';
    final season          = data['season']             as String;
    final emoji           = data['season_emoji']       as String;
    final nextSeason      = data['next_season']        as String;
    final nextEmoji       = data['next_season_emoji']  as String;
    final collectedDays   = (data['collected_days']    as num).toInt();
    final daysMissed      = (data['days_missed']       as num? ?? 0).toInt();
    final daysRemaining   = (data['days_remaining']    as num? ?? 0).toInt();
    final daysElapsed     = (data['days_elapsed']      as num? ?? collectedDays).toInt();
    final totalDays       = (data['total_days']        as num).toInt();
    final daysOffline     = (data['days_offline']      as num? ?? 0).toInt();
    final lastReadingDate = data['last_reading_date']  as String?;
    final displayStart    = data['display_start'] as String?
                         ?? data['season_start']  as String? ?? '';
    final nextSeasonEnd   = data['next_season_end'] as String? ?? '';

    final monthLabels = (displayStart.isNotEmpty && nextSeasonEnd.isNotEmpty)
        ? _monthRange(displayStart, nextSeasonEnd)
        : <String>[];

    const totalWeeks   = 12;
    final elapsedWeeks = totalDays > 0
        ? ((daysElapsed / totalDays) * totalWeeks).round().clamp(0, totalWeeks) : 0;
    final weeksLeft    = (daysRemaining / 7).round().clamp(0, 52);

    return RefreshIndicator(
      color: AppColors.mint,
      onRefresh: () async => onRefresh(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _PageHeader(city: city, season: season, emoji: emoji,
            infoTitle: 'Why No Forecast Yet?',
            infoBody: 'To deliver a reliable personalized forecast, we need data '
                      'from a complete season.\n\nSince you joined near the end of '
                      '${_cap(season)}, we\'ll continue collecting through '
                      '${_cap(nextSeason)} to ensure accuracy.\n\n'
                      'You\'ll see your first forecast when ${_cap(nextSeason)} ends.'),
          const SizedBox(height: 20),
          if (daysOffline > 0) ...[
            _DailyMissingWarning(daysOffline: daysOffline, lastReadingDate: lastReadingDate),
            const SizedBox(height: 12),
          ],
          GlassCard(radius: 18, padding: const EdgeInsets.all(16), child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
              const _CardHeader(icon: Icons.hourglass_bottom_rounded,
                color: Color(0xFFFF9C3B),
                title: 'Forecast Not Available Yet',
                subtitle: 'Extending data collection to next season'),
              const SizedBox(height: 12),
              Text('You joined near the end of ${_cap(season)}. '
                   'We\'ll keep collecting through ${_cap(nextSeason)} $nextEmoji '
                   'so your first forecast is built on a full season of your data.',
                style: const TextStyle(fontSize: 12, color: AppColors.sub, height: 1.5)),
            ])),
          const SizedBox(height: 12),
          GlassCard(radius: 18, padding: const EdgeInsets.all(16), child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Data Collection — ${_cap(season)} $emoji \u2192 ${_cap(nextSeason)} $nextEmoji',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
              const SizedBox(height: 16),
              _SeasonTimeline(
                totalWeeks: totalWeeks,
                elapsedWeeks: elapsedWeeks,
                seasonStart: displayStart,
                customLabels: monthLabels.isNotEmpty ? monthLabels : null,
                // directProgress corrects the dot position for partial months
                directProgress: (displayStart.isNotEmpty && nextSeasonEnd.isNotEmpty)
                    ? _toMonthProgress(displayStart, nextSeasonEnd, daysElapsed)
                    : null,
              ),
              const SizedBox(height: 10),
              _StatsRow(collectedDays: collectedDays, daysMissed: daysMissed, daysRemaining: daysRemaining),
              if (weeksLeft > 0) ...[
                const SizedBox(height: 14),
                _NoteBox(icon: Icons.schedule_rounded, color: const Color(0xFFFF9C3B),
                  text: '$weeksLeft week${weeksLeft == 1 ? '' : 's'} remaining until '
                        '${_cap(nextSeason)} ends. Your first forecast will be ready then.'),
              ],
            ])),
          const SizedBox(height: 12),
          const _Disclaimer(),
        ])));
  }
}


// ═══════════════════════════════════════════════════════════
//  CASE: forecast_available
//  Previous season data is complete (≥ 45 days collected).
//  Personalized forecast is computed and displayed.
//
//  α (alpha) — personalized performance factor:
//    α = sumActual / sumExpected
//    Computed here in Flutter to keep the backend stateless.
//    α is never stored — it is recalculated on each page open.
//    Forecast = α × GHI_future × PR × P_nom × days
// ═══════════════════════════════════════════════════════════

class _ForecastAvailableCase extends StatefulWidget {
  final Map<String, dynamic> data;
  final VoidCallback onRefresh;
  const _ForecastAvailableCase({required this.data, required this.onRefresh});
  @override State<_ForecastAvailableCase> createState() => _ForecastAvailableCaseState();
}

class _ForecastAvailableCaseState extends State<_ForecastAvailableCase> {
  late int _forecastYear;
  late double _alpha;
  late List<double> _actual;
  late List<double> _predicted;
  late List<String> _monthLabels;
  late int _baseYear;
  late List<int> _forecastYears;

  @override
  void initState() { super.initState(); _compute(); }

  void _compute() {
    final data       = widget.data;
    final prevSeason = data['prev_season']       as String;
    final prevStart  = data['prev_season_start'] as String? ?? '';
    final panelCap   = (data['panel_capacity']   as num? ?? 5.0).toDouble();
    final rawActual  = data['actual_by_month']   as Map<String, dynamic>? ?? {};

    final sortedKeys = rawActual.keys.toList()..sort();
    _actual = sortedKeys.map((k) => (rawActual[k] as num).toDouble()).toList();
    _monthLabels = sortedKeys.map((k) {
      const mn = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return mn[int.tryParse(k.split('-')[1]) ?? 1];
    }).toList();

    final months = _seasonMonthNums(prevSeason);
    final sumExp = months.map((m) => _eExpected(m, panelCap)).fold(0.0, (a, b) => a + b);
    final sumAct = _actual.fold(0.0, (a, b) => a + b);

    // α = actual / expected — personalizes the GHI-based projection
    _alpha        = sumExp > 0 ? sumAct / sumExp : 1.0;
    _baseYear     = prevStart.isNotEmpty ? int.parse(prevStart.split('-')[0]) : DateTime.now().year;
    _forecastYears = [_baseYear + 1, _baseYear + 2];
    _forecastYear  = _forecastYears.first;
    _predicted     = _buildForecast(_forecastYear, months, panelCap);
  }

  List<double> _buildForecast(int year, List<int> months, double panelCap) {
    final yearDelta = year - _baseYear;
    return months.map((m) => _eExpectedFuture(m, panelCap, yearDelta) * _alpha).toList();
  }

  void _onYearChanged(int year) {
    final data       = widget.data;
    final prevSeason = data['prev_season'] as String;
    final panelCap   = (data['panel_capacity'] as num? ?? 5.0).toDouble();
    setState(() {
      _forecastYear = year;
      _predicted    = _buildForecast(year, _seasonMonthNums(prevSeason), panelCap);
    });
  }

  @override
  Widget build(BuildContext context) {
    final data            = widget.data;
    final city            = data['city']              as String? ?? '';
    final season          = data['season']             as String;
    final emoji           = data['season_emoji']       as String;
    final prevSeason      = data['prev_season']        as String;
    final prevEmoji       = data['prev_season_emoji']  as String;
    final collectedDays   = (data['collected_days']    as num).toInt();
    final daysMissed      = (data['days_missed']       as num? ?? 0).toInt();
    final daysRemaining   = (data['days_remaining']    as num? ?? 0).toInt();
    final daysElapsed     = (data['days_elapsed']      as num? ?? 0).toInt();
    final totalDays       = (data['total_days']        as num).toInt();
    final daysOffline     = (data['days_offline']      as num? ?? 0).toInt();
    final lastReadingDate = data['last_reading_date']  as String?;

    final sumActual    = _actual.fold(0.0, (a, b) => a + b);
    final sumPredicted = _predicted.fold(0.0, (a, b) => a + b);
    final pct  = sumActual > 0 ? (sumPredicted - sumActual) / sumActual * 100 : 0.0;
    final isUp = pct >= 0;
    final clr  = isUp ? AppColors.mint : const Color(0xFFFF5A52);
    final sign = isUp ? '+' : '';

    const totalWeeks   = 12;
    final elapsedWeeks = totalDays > 0
        ? ((daysElapsed / totalDays) * totalWeeks).round().clamp(0, totalWeeks) : 0;

    return RefreshIndicator(
      color: AppColors.mint,
      onRefresh: () async => widget.onRefresh(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            _PillCity(city),
            const SizedBox(width: 8),
            _PillSeason(emoji: prevEmoji, label: '${_cap(prevSeason)} Forecast'),
            const Spacer(),
            _InfoBtn(title: 'Your Personalized Forecast',
              body: 'This forecast is built from your actual ${_cap(prevSeason)} production data.\n\n'
                    'We calculate your system\'s real-world performance factor, '
                    'then apply it to future GHI solar radiation projections to '
                    'predict your production for the same season next year.\n\n'
                    'The dashed line shows your actual ${_cap(prevSeason)} output. '
                    'The solid line shows the predicted output for the selected year.\n\n'
                    'Methodology: IEC TS 61724-3 / NREL PVWatts (Dobos, 2014).'),
          ]),
          const SizedBox(height: 14),
          _YearSel(years: _forecastYears, selected: _forecastYear, onChanged: _onYearChanged),
          const SizedBox(height: 14),
          if (_actual.isNotEmpty && _predicted.isNotEmpty)
            _SeasonChartCard(
              prevSeason: prevSeason, prevEmoji: prevEmoji,
              baseYear: _baseYear, forecastYear: _forecastYear,
              actual: _actual, predicted: _predicted,
              monthLabels: _monthLabels,
            ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: GlassCard(radius: 18, padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Expected Change $_forecastYear',
                  style: const TextStyle(fontSize: 11, color: AppColors.sub)),
                const SizedBox(height: 8),
                Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Text('$sign${pct.toStringAsFixed(1)}%',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900, color: clr)),
                  const SizedBox(width: 4),
                  Padding(padding: const EdgeInsets.only(bottom: 2),
                    child: Icon(isUp ? Icons.trending_up_rounded : Icons.trending_down_rounded,
                      color: clr, size: 16)),
                ]),
                const SizedBox(height: 3),
                Text('vs ${_cap(prevSeason)} $_baseYear',
                  style: const TextStyle(fontSize: 11, color: AppColors.sub)),
              ]))),
            const SizedBox(width: 10),
            Expanded(child: GlassCard(radius: 18, padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_cap(prevSeason)} Avg $_forecastYear',
                  style: const TextStyle(fontSize: 11, color: AppColors.sub)),
                const SizedBox(height: 8),
                FittedBox(fit: BoxFit.scaleDown, alignment: Alignment.centerLeft,
                  child: Text(
                    _predicted.isNotEmpty
                        ? '${(_predicted.fold(0.0,(a,b)=>a+b)/_predicted.length).toStringAsFixed(0)} kWh'
                        : '—',
                    style: const TextStyle(fontSize: 22,
                      fontWeight: FontWeight.w900, color: AppColors.text))),
                const SizedBox(height: 3),
                const Text('monthly avg forecast',
                  style: TextStyle(fontSize: 11, color: AppColors.sub)),
              ]))),
          ]),
          const SizedBox(height: 12),
          // Investment recommendation threshold: 10% IRR (above S&P 500 average)
          _TileCard(
            icon: pct >= 10 ? Icons.lightbulb_rounded : Icons.info_outline_rounded,
            color: pct >= 10 ? AppColors.cyan : const Color(0xFFFF9C3B),
            title: pct >= 10 ? 'Investment Recommended' : 'Hold Your Investment',
            body: pct >= 10
                ? 'Solar forecasts for your system look promising. Expanding your '
                  'installation — adding panels or upgrading battery storage — is '
                  'expected to yield returns above the 10% threshold.'
                : 'Based on your system\'s forecast, a major expansion is not '
                  'recommended at this time. Monitor trends before investing further.',
          ),
          const SizedBox(height: 12),
          if (daysOffline > 0) ...[
            _DailyMissingWarning(daysOffline: daysOffline, lastReadingDate: lastReadingDate),
            const SizedBox(height: 12),
          ],
          GlassCard(radius: 18, padding: const EdgeInsets.all(16), child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
              _CardHeader(
                icon: Icons.data_thresholding_outlined,
                color: AppColors.cyan,
                title: 'Now Collecting — ${_cap(season)} $emoji',
                subtitle: 'Next forecast: ${_cap(season)} ${_baseYear + 1} & ${_baseYear + 2}'),
              const SizedBox(height: 14),
              _SeasonTimeline(totalWeeks: totalWeeks, elapsedWeeks: elapsedWeeks,
                seasonStart: data['season_start'] as String? ?? '',
                compact: true),
              const SizedBox(height: 10),
              _StatsRow(collectedDays: collectedDays, daysMissed: daysMissed, daysRemaining: daysRemaining),
            ])),
          const SizedBox(height: 12),
          const _Disclaimer(),
        ])));
  }
}


// ═══════════════════════════════════════════════════════════
//  CASE: feature_disabled
//  Device offline ≥ 15 days — forecast paused.
// ═══════════════════════════════════════════════════════════

class _FeatureDisabled extends StatelessWidget {
  final Map<String, dynamic> data;
  final Future<void> Function() onCheck;
  const _FeatureDisabled({required this.data, required this.onCheck});
  static const _red = Color(0xFFFF5A52);

  @override
  Widget build(BuildContext context) {
    final city            = data['city']             as String? ?? '';
    final daysOffline     = (data['days_offline']    as num? ?? 15).toInt();
    final lastReadingDate = data['last_reading_date'] as String?;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
      child: Column(children: [
        Row(children: [
          if (city.isNotEmpty) _PillCity(city),
          const SizedBox(width: 8),
          const _PillOffline(),
        ]),
        const SizedBox(height: 28),
        Container(width: 80, height: 80,
          decoration: BoxDecoration(color: _red.withOpacity(0.12), shape: BoxShape.circle),
          child: Center(child: Text('!',
            style: TextStyle(fontSize: 40, fontWeight: FontWeight.w900,
              color: _red, fontFamily: 'Georgia', height: 1)))),
        const SizedBox(height: 16),
        const Text('Solar Forecast Paused',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        Padding(padding: const EdgeInsets.symmetric(horizontal: 20),
          child: RichText(textAlign: TextAlign.center, text: TextSpan(
            style: const TextStyle(fontSize: 12, color: AppColors.sub, height: 1.5),
            children: [
              const TextSpan(text: "Your solar device hasn't sent data for "),
              TextSpan(text: '$daysOffline days',
                style: const TextStyle(color: _red, fontWeight: FontWeight.w800)),
              const TextSpan(text: '. Reconnect your device to resume data collection.'),
            ]))),
        const SizedBox(height: 28),
        GlassCard(radius: 18, padding: const EdgeInsets.all(16), child: Column(
          crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _IconBox(icon: Icons.power_settings_new_rounded, color: _red),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Connection Lost',
                  style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: _red)),
                const SizedBox(height: 2),
                Text('Last reading received $daysOffline days ago',
                  style: const TextStyle(fontSize: 11, color: AppColors.sub)),
              ])),
            ]),
            const SizedBox(height: 14),
            if (lastReadingDate != null) ...[
              _Row2(label: 'Last reading', value: _fmtDate(lastReadingDate), valueColor: _red),
              const Divider(color: Colors.white10, height: 20),
            ],
            _Row2(label: 'Days offline', value: '$daysOffline days', valueColor: _red),
            const SizedBox(height: 12),
            const _NoteBox(icon: Icons.info_outline_rounded, color: _red,
              text: 'Solar Forecast requires regular readings from your production device. '
                    'Collection resumes automatically once reconnected.'),
          ])),
        const SizedBox(height: 16),
        SizedBox(width: double.infinity,
          child: ElevatedButton(onPressed: onCheck,
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.button,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
            child: const Text('Check Device Connection',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900)))),
      ]));
  }
}


// ═══════════════════════════════════════════════════════════
//  SHARED WIDGET: _StatsRow
//  Displays collected / missed / remaining day counts.
//  Used by: collecting, collecting_extended, forecast_available.
// ═══════════════════════════════════════════════════════════

class _StatsRow extends StatelessWidget {
  final int collectedDays, daysMissed, daysRemaining;
  const _StatsRow({
    required this.collectedDays,
    required this.daysMissed,
    required this.daysRemaining,
  });

  @override
  Widget build(BuildContext context) => Row(children: [
    _StatChip(value: '$collectedDays', label: 'Days collected'),
    const SizedBox(width: 10),
    _StatChip(value: '$daysMissed',    label: 'Days missed'),
    const SizedBox(width: 10),
    _StatChip(value: '$daysRemaining', label: 'Days remaining'),
  ]);
}


// ═══════════════════════════════════════════════════════════
//  DAILY MISSING WARNING
// ═══════════════════════════════════════════════════════════

class _DailyMissingWarning extends StatelessWidget {
  final int daysOffline;
  final String? lastReadingDate;
  const _DailyMissingWarning({required this.daysOffline, this.lastReadingDate});
  static const _yellow = Color(0xFFFFC56B);

  @override
  Widget build(BuildContext context) {
    final sinceStr = lastReadingDate != null ? _fmtDate(lastReadingDate!) : '—';
    String missedStr = '—';
    if (lastReadingDate != null) {
      try {
        final firstMissed = DateTime.parse(lastReadingDate!).add(const Duration(days: 1));
        missedStr = _fmtDate(firstMissed.toIso8601String());
      } catch (_) {}
    }

    return GlassCard(radius: 18, padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          _IconBox(icon: Icons.warning_amber_rounded, color: _yellow),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('No Data Collected Today',
              style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: _yellow)),
            const SizedBox(height: 2),
            Text(missedStr, style: const TextStyle(fontSize: 11, color: AppColors.sub)),
          ])),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(color: _yellow.withOpacity(0.12),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: _yellow.withOpacity(0.25))),
            child: Text('Day $daysOffline / 15',
              style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: _yellow))),
        ]),
        const SizedBox(height: 12),
        _Row2(label: 'Missing since', value: sinceStr),
        const Divider(color: Colors.white10, height: 16),
        const _Row2(label: 'Timeline', value: 'Continues \u2014 gap recorded'),
        const SizedBox(height: 10),
        const _NoteBox(icon: Icons.info_outline_rounded, color: _yellow,
          text: 'We couldn\'t read your production device. Check your connection. '
                'After 15 days without data, Solar Forecast will be paused.'),
      ]));
  }
}


// ═══════════════════════════════════════════════════════════
//  SEASON TIMELINE
// ═══════════════════════════════════════════════════════════

class _SeasonTimeline extends StatelessWidget {
  final int totalWeeks, elapsedWeeks;
  final bool extendToNext, compact;
  final String seasonStart;
  final String? nextSeasonStart;
  final List<String>? customLabels;
  final double? directProgress;

  const _SeasonTimeline({
    required this.totalWeeks, required this.elapsedWeeks,
    required this.seasonStart,
    this.extendToNext = false, this.compact = false,
    this.nextSeasonStart, this.customLabels,
    this.directProgress,
  });

  static const _mn = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  List<String> _buildLabels() {
    if (customLabels != null) return customLabels!;
    final m = int.parse(seasonStart.split('-')[1]);
    final labels = <String>[];
    for (int i = 0; i < 3; i++) labels.add(_mn[((m - 1 + i) % 12) + 1]);
    if (extendToNext && nextSeasonStart != null) {
      final nm = int.parse(nextSeasonStart!.split('-')[1]);
      for (int i = 0; i < 3; i++) labels.add(_mn[((nm - 1 + i) % 12) + 1]);
    }
    return labels;
  }

  @override
  Widget build(BuildContext context) {
    final labels   = _buildLabels();
    final dotCount = labels.length + 1;
    final dimAfter = (extendToNext && customLabels == null) ? 4 : null;
    final progress = directProgress ?? (totalWeeks > 0 ? elapsedWeeks / totalWeeks : 0.0);

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        for (int i = 0; i < labels.length; i++)
          Expanded(child: Center(child: Text(labels[i],
            style: TextStyle(fontSize: compact ? 10 : 11, fontWeight: FontWeight.w700,
              color: (extendToNext && customLabels == null && i >= 3)
                  ? AppColors.sub.withOpacity(0.4) : AppColors.sub)))),
      ]),
      const SizedBox(height: 8),
      SizedBox(height: compact ? 26 : 34, child: CustomPaint(
        painter: _TimelinePainter(totalSegments: dotCount, progress: progress, dimAfter: dimAfter),
        child: const SizedBox.expand())),
    ]);
  }
}

class _TimelinePainter extends CustomPainter {
  final int totalSegments; final double progress; final int? dimAfter;
  const _TimelinePainter({required this.totalSegments, required this.progress, this.dimAfter});

  @override
  void paint(Canvas canvas, Size size) {
    const r = 6.0;
    final mid = size.height / 2;
    final gap = size.width / (totalSegments - 1 + 0.001);
    final primary = dimAfter ?? totalSegments;

    canvas.drawRRect(RRect.fromRectAndRadius(
      Rect.fromLTWH(0, mid-3, size.width, 6), const Radius.circular(3)),
      Paint()..color = AppColors.cyan.withOpacity(0.10));

    final filled = (progress * (primary-1) / (totalSegments-1)) * size.width;
    if (filled > 0) canvas.drawRRect(RRect.fromRectAndRadius(
      Rect.fromLTWH(0, mid-3, filled, 6), const Radius.circular(3)),
      Paint()..color = AppColors.cyan);

    for (int i = 0; i < totalSegments; i++) {
      final x     = i * gap;
      final isDim = dimAfter != null && i >= dimAfter!;
      final prog  = isDim ? 0.0 : ((progress*(primary-1)-i).clamp(0.0,1.0));
      final done  = prog >= 1.0;
      canvas.drawCircle(Offset(x,mid), r+2,
        Paint()..color = isDim ? AppColors.cyan.withOpacity(0.04) : AppColors.cyan.withOpacity(0.15));
      canvas.drawCircle(Offset(x,mid), r,
        Paint()..color = done ? AppColors.cyan : isDim ? AppColors.cyan.withOpacity(0.08) : AppColors.cyan.withOpacity(0.30));
      if (done) {
        final p = Paint()..color=Colors.black..strokeWidth=1.5..style=PaintingStyle.stroke..strokeCap=StrokeCap.round;
        canvas.drawLine(Offset(x-2.5,mid), Offset(x-0.5,mid+2), p);
        canvas.drawLine(Offset(x-0.5,mid+2), Offset(x+2.5,mid-2), p);
      }
    }
    if (filled > 0 && filled < size.width) {
      canvas.drawCircle(Offset(filled,mid), 5, Paint()..color=AppColors.cyan);
      canvas.drawCircle(Offset(filled,mid), 3, Paint()..color=Colors.white);
    }
  }

  @override bool shouldRepaint(covariant _TimelinePainter o) => o.progress != progress;
}


// ═══════════════════════════════════════════════════════════
//  SEASON CHART CARD (forecast_available only)
// ═══════════════════════════════════════════════════════════

class _SeasonChartCard extends StatelessWidget {
  final String prevSeason, prevEmoji;
  final int baseYear, forecastYear;
  final List<double> actual, predicted;
  final List<String> monthLabels;

  const _SeasonChartCard({
    required this.prevSeason, required this.prevEmoji,
    required this.baseYear,   required this.forecastYear,
    required this.actual,     required this.predicted,
    required this.monthLabels,
  });

  @override
  Widget build(BuildContext context) => GlassCard(
    radius: 20, padding: const EdgeInsets.all(16),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_cap(prevSeason)} Production Forecast',
            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
          const SizedBox(height: 2),
          const Text('kWh per month',
            style: TextStyle(fontSize: 11, color: AppColors.sub)),
        ])),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          _LegItem(color: AppColors.mint, label: 'Forecast $forecastYear'),
          const SizedBox(height: 3),
          _LegItem(color: AppColors.mint.withOpacity(0.3),
            label: '${_cap(prevSeason)} $baseYear', dashed: true),
        ]),
      ]),
      const SizedBox(height: 14),
      SizedBox(height: 155, child: CustomPaint(
        painter: _ChartPainter(actual: actual, predicted: predicted),
        child: const SizedBox.expand())),
      const SizedBox(height: 6),
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: monthLabels.map((m) =>
          Text(m, style: const TextStyle(fontSize: 10, color: AppColors.sub))).toList()),
    ]));
}

class _ChartPainter extends CustomPainter {
  final List<double> actual, predicted;
  const _ChartPainter({required this.actual, required this.predicted});

  @override
  void paint(Canvas canvas, Size size) {
    if (actual.isEmpty || predicted.isEmpty) return;
    final maxV = [...actual,...predicted].reduce((a,b)=>a>b?a:b)*1.2;
    const pL=36.0, pR=8.0, pT=8.0, pB=4.0;
    final w=size.width-pL-pR, h=size.height-pT-pB;
    final n=actual.length;

    Offset pt(int i, double v) => Offset(pL+w*i/(n-1), pT+h*(1-v/maxV));

    final lStyle = TextStyle(fontSize:9, color:AppColors.sub.withOpacity(0.65));
    for (int g=0; g<=3; g++) {
      final y=pT+h*g/3;
      final tp=TextPainter(text:TextSpan(text:(maxV*(1-g/3)).toInt().toString(),style:lStyle),
        textDirection:TextDirection.ltr)..layout();
      tp.paint(canvas, Offset(0, y-tp.height/2));
      canvas.drawLine(Offset(pL,y), Offset(pL+w,y),
        Paint()..color=Colors.white.withOpacity(0.06)..strokeWidth=1);
    }

    final dPath = Path()..moveTo(pt(0,actual[0]).dx, pt(0,actual[0]).dy);
    for (int i=1;i<n;i++) dPath.lineTo(pt(i,actual[i]).dx, pt(i,actual[i]).dy);
    _drawDashed(canvas, dPath,
      Paint()..color=AppColors.mint.withOpacity(0.28)..strokeWidth=1.5..style=PaintingStyle.stroke);

    final fPts = List.generate(n, (i)=>pt(i,predicted[i]));
    final fill = Path()..moveTo(fPts[0].dx, pT+h);
    for (final p in fPts) fill.lineTo(p.dx, p.dy);
    fill.lineTo(fPts.last.dx, pT+h); fill.close();
    canvas.drawPath(fill, Paint()..shader=LinearGradient(
      begin:Alignment.topCenter, end:Alignment.bottomCenter,
      colors:[AppColors.mint.withOpacity(0.20), Colors.transparent],
    ).createShader(Rect.fromLTWH(0,pT,size.width,h)));

    final fLine=Path()..moveTo(fPts[0].dx,fPts[0].dy);
    for (int i=1;i<n;i++) fLine.lineTo(fPts[i].dx,fPts[i].dy);
    canvas.drawPath(fLine,
      Paint()..color=AppColors.mint..strokeWidth=2.5..style=PaintingStyle.stroke..strokeCap=StrokeCap.round);

    for (final p in fPts) {
      canvas.drawCircle(p, 6, Paint()..color=AppColors.mint.withOpacity(0.15));
      canvas.drawCircle(p, 3.2, Paint()..color=AppColors.mint);
    }
  }

  void _drawDashed(Canvas c, Path path, Paint paint) {
    for (final m in path.computeMetrics()) {
      double d=0; bool draw=true;
      while (d<m.length) {
        final end=(d+(draw?5.0:4.0)).clamp(0.0,m.length);
        if (draw) c.drawPath(m.extractPath(d,end),paint);
        d=end; draw=!draw;
      }
    }
  }

  @override
  bool shouldRepaint(covariant _ChartPainter o) =>
    o.actual!=actual || o.predicted!=predicted;
}


// ═══════════════════════════════════════════════════════════
//  YEAR SELECTOR
// ═══════════════════════════════════════════════════════════

class _YearSel extends StatelessWidget {
  final List<int> years; final int selected; final ValueChanged<int> onChanged;
  const _YearSel({required this.years, required this.selected, required this.onChanged});

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(4),
    decoration: BoxDecoration(color: AppColors.card2,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: AppColors.stroke)),
    child: Row(children: years.map((y) {
      final active = y==selected;
      return Expanded(child: GestureDetector(
        onTap: ()=>onChanged(y),
        child: AnimatedContainer(
          duration: const Duration(milliseconds:200), curve:Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(vertical:9),
          decoration: BoxDecoration(
            color: active?AppColors.mint.withOpacity(0.16):Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color:active?AppColors.mint.withOpacity(0.35):Colors.transparent)),
          child: Center(child: Text('$y', style: TextStyle(
            fontSize:13, fontWeight:FontWeight.w800,
            color:active?AppColors.mint:AppColors.sub))))));
    }).toList()));
}


// ═══════════════════════════════════════════════════════════
//  LEGEND ITEM
// ═══════════════════════════════════════════════════════════

class _LegItem extends StatelessWidget {
  final Color color; final String label; final bool dashed;
  const _LegItem({required this.color, required this.label, this.dashed=false});

  @override
  Widget build(BuildContext context) => Row(mainAxisSize:MainAxisSize.min, children: [
    SizedBox(width:18, height:3, child: dashed
        ? CustomPaint(painter:_DashLinePainter(color:color))
        : DecoratedBox(decoration:BoxDecoration(color:color,
            borderRadius:BorderRadius.circular(99)))),
    const SizedBox(width:5),
    Text(label, style:const TextStyle(fontSize:10, color:AppColors.sub)),
  ]);
}

class _DashLinePainter extends CustomPainter {
  final Color color; const _DashLinePainter({required this.color});
  @override void paint(Canvas c, Size s) {
    final p=Paint()..color=color..strokeWidth=1.5;
    double x=0;
    while (x<s.width) {
      c.drawLine(Offset(x,s.height/2), Offset((x+4).clamp(0.0,s.width),s.height/2),p);
      x+=7;
    }
  }
  @override bool shouldRepaint(_)=>false;
}


// ═══════════════════════════════════════════════════════════
//  TILE CARD
// ═══════════════════════════════════════════════════════════

class _TileCard extends StatelessWidget {
  final IconData icon; final Color color; final String title, body;
  const _TileCard({required this.icon, required this.color,
    required this.title, required this.body});

  @override
  Widget build(BuildContext context) => GlassCard(
    radius:18, padding:const EdgeInsets.all(14),
    child:Row(crossAxisAlignment:CrossAxisAlignment.start, children:[
      Container(width:40, height:40,
        decoration:BoxDecoration(color:color.withOpacity(0.14),
          borderRadius:BorderRadius.circular(12)),
        child:Icon(icon, color:color, size:20)),
      const SizedBox(width:12),
      Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start, children:[
        Text(title, style:TextStyle(fontSize:13.5, fontWeight:FontWeight.w800, color:color)),
        const SizedBox(height:5),
        Text(body, style:const TextStyle(fontSize:12, color:AppColors.sub, height:1.45)),
      ])),
    ]));
}


// ═══════════════════════════════════════════════════════════
//  SHARED UI WIDGETS
// ═══════════════════════════════════════════════════════════

class _PageHeader extends StatelessWidget {
  final String city, season, emoji, infoTitle, infoBody;
  const _PageHeader({required this.city, required this.season, required this.emoji,
    required this.infoTitle, required this.infoBody});
  @override
  Widget build(BuildContext context) => Row(children: [
    _PillCity(city), const SizedBox(width:8),
    _PillSeason(emoji:emoji, label:_cap(season)),
    const Spacer(),
    _InfoBtn(title:infoTitle, body:infoBody),
  ]);
}

class _IconBox extends StatelessWidget {
  final IconData icon; final Color color;
  const _IconBox({required this.icon, required this.color});
  @override
  Widget build(BuildContext context) => Container(width:36, height:36,
    decoration:BoxDecoration(color:color.withOpacity(0.14),
      borderRadius:BorderRadius.circular(10)),
    child:Icon(icon, color:color, size:18));
}

class _CardHeader extends StatelessWidget {
  final IconData icon; final Color color; final String title, subtitle;
  const _CardHeader({required this.icon, required this.color,
    required this.title, required this.subtitle});
  @override
  Widget build(BuildContext context) => Row(children:[
    _IconBox(icon:icon, color:color), const SizedBox(width:10),
    Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start, children:[
      Text(title, style:TextStyle(fontSize:13.5, fontWeight:FontWeight.w800, color:color)),
      const SizedBox(height:2),
      Text(subtitle, style:const TextStyle(fontSize:11, color:AppColors.sub)),
    ])),
  ]);
}

class _NoteBox extends StatelessWidget {
  final IconData icon; final Color color; final String text;
  const _NoteBox({required this.icon, required this.color, required this.text});
  @override
  Widget build(BuildContext context) => Container(
    padding:const EdgeInsets.symmetric(horizontal:10, vertical:8),
    decoration:BoxDecoration(color:color.withOpacity(0.07),
      borderRadius:BorderRadius.circular(10)),
    child:Row(crossAxisAlignment:CrossAxisAlignment.start, children:[
      Icon(icon, size:13, color:color), const SizedBox(width:7),
      Expanded(child:Text(text,
        style:const TextStyle(fontSize:11, color:AppColors.sub, height:1.4))),
    ]));
}

class _Row2 extends StatelessWidget {
  final String label, value; final Color? valueColor;
  const _Row2({required this.label, required this.value, this.valueColor});
  @override
  Widget build(BuildContext context) => Row(
    mainAxisAlignment:MainAxisAlignment.spaceBetween, children:[
      Text(label, style:const TextStyle(fontSize:12, color:AppColors.sub)),
      Text(value, style:TextStyle(fontSize:12, fontWeight:FontWeight.w700,
        color:valueColor??AppColors.text)),
    ]);
}

class _StatChip extends StatelessWidget {
  final String value, label;
  const _StatChip({required this.value, required this.label});
  @override
  Widget build(BuildContext context) => Expanded(
    child:Container(
      padding:const EdgeInsets.symmetric(vertical:10),
      decoration:BoxDecoration(color:AppColors.cyan.withOpacity(0.06),
        borderRadius:BorderRadius.circular(12),
        border:Border.all(color:AppColors.cyan.withOpacity(0.12))),
      child:Column(children:[
        Text(value, style:const TextStyle(fontSize:20, fontWeight:FontWeight.w900, color:AppColors.cyan)),
        const SizedBox(height:2),
        Text(label, style:const TextStyle(fontSize:10, color:AppColors.sub)),
      ])));
}

class _PillCity extends StatelessWidget {
  final String city; const _PillCity(this.city);
  @override
  Widget build(BuildContext context) => _Pill(child:Row(mainAxisSize:MainAxisSize.min, children:[
    Container(width:7, height:7, decoration:BoxDecoration(color:AppColors.mint,
      shape:BoxShape.circle,
      boxShadow:[BoxShadow(color:AppColors.mint.withOpacity(0.5),blurRadius:5)])),
    const SizedBox(width:6),
    Text(city, style:const TextStyle(fontSize:12.5, fontWeight:FontWeight.w700, color:AppColors.mint)),
  ]));
}

class _PillSeason extends StatelessWidget {
  final String emoji, label; const _PillSeason({required this.emoji, required this.label});
  @override
  Widget build(BuildContext context) => _Pill(child:Row(mainAxisSize:MainAxisSize.min, children:[
    Text(emoji, style:const TextStyle(fontSize:12)), const SizedBox(width:5),
    Text(label, style:const TextStyle(fontSize:12.5, fontWeight:FontWeight.w700, color:AppColors.sub)),
  ]));
}

class _PillOffline extends StatelessWidget {
  const _PillOffline();
  @override
  Widget build(BuildContext context) => _Pill(child:Row(mainAxisSize:MainAxisSize.min, children:[
    Container(width:7, height:7, decoration:BoxDecoration(
      color:const Color(0xFFFF5A52), shape:BoxShape.circle,
      boxShadow:[BoxShadow(color:const Color(0xFFFF5A52).withOpacity(0.5),blurRadius:5)])),
    const SizedBox(width:6),
    const Text('Device Offline', style:TextStyle(fontSize:12.5,
      fontWeight:FontWeight.w700, color:Color(0xFFFF5A52))),
  ]));
}

class _Pill extends StatelessWidget {
  final Widget child; const _Pill({required this.child});
  @override
  Widget build(BuildContext context) => Container(
    padding:const EdgeInsets.symmetric(horizontal:12, vertical:7),
    decoration:BoxDecoration(color:AppColors.card2, borderRadius:BorderRadius.circular(30),
      border:Border.all(color:AppColors.stroke)),
    child:child);
}

class _InfoBtn extends StatelessWidget {
  final String title, body; const _InfoBtn({required this.title, required this.body});
  @override
  Widget build(BuildContext context) => IconButton(
    icon:Icon(Icons.info_outline_rounded, size:20, color:AppColors.sub.withOpacity(0.6)),
    onPressed:()=>showDialog(context:context,
      builder:(_)=>AlertDialog(
        backgroundColor:const Color(0xFF1E2A2A),
        shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(20)),
        title:Text(title, style:const TextStyle(fontSize:15, fontWeight:FontWeight.w800)),
        content:Text(body, style:const TextStyle(fontSize:13, color:AppColors.sub, height:1.55)),
        actions:[TextButton(onPressed:()=>Navigator.pop(context),
          child:const Text('Got it',
            style:TextStyle(color:AppColors.mint, fontWeight:FontWeight.w700)))])));
}

class _Disclaimer extends StatelessWidget {
  final bool noPanels; const _Disclaimer({this.noPanels=false});
  @override
  Widget build(BuildContext context) => GlassCard(
    radius:14, padding:const EdgeInsets.symmetric(horizontal:12, vertical:10),
    child:Row(children:[
      Icon(Icons.info_outline_rounded, size:14, color:AppColors.sub.withOpacity(0.7)),
      const SizedBox(width:8),
      Expanded(child:Text(
        noPanels
            ? 'These are estimated figures based on GHI solar radiation data for your region '
              'and a standard 5 kWp reference system.'
            : 'Forecasts are based on your production data and GHI solar radiation models. '
              'Actual output may vary due to weather, panel condition, and system changes.',
        style:const TextStyle(fontSize:11, color:AppColors.sub, height:1.4))),
    ]));
}


// ═══════════════════════════════════════════════════════════
//  HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════

/// Convert linear day progress into a month-accurate timeline position.
/// Fixes the partial-month dot placement in collecting_extended
/// (e.g. Nov 20–30 = 10 days, not a full month segment).
double _toMonthProgress(
  String displayStartIso,
  String endDateIso,
  int daysElapsed,
) {
  try {
    final start = DateTime.parse(displayStartIso);
    final end   = DateTime.parse(endDateIso);
    final today = start.add(Duration(days: daysElapsed > 0 ? daysElapsed - 1 : 0));

    final months = <DateTime>[];
    var cur = DateTime(start.year, start.month, 1);
    while (!cur.isAfter(DateTime(end.year, end.month, 1))) {
      months.add(cur);
      cur = DateTime(cur.year, cur.month + 1, 1);
    }

    final n = months.length;
    if (n == 0) return 0.0;

    for (int i = 0; i < n; i++) {
      final segStart = i == 0 ? start : months[i];
      final segEnd   = i < n - 1
          ? months[i + 1].subtract(const Duration(days: 1))
          : end;

      if (!today.isAfter(segEnd)) {
        final segLen  = segEnd.difference(segStart).inDays + 1;
        final elapsed = today.difference(segStart).inDays + 1;
        final frac    = segLen > 0 ? elapsed.clamp(0, segLen) / segLen : 0.0;
        return (i + frac) / n;
      }
    }
    return 1.0;
  } catch (_) {
    return 0.0;
  }
}

/// Capitalize the first letter of a string.
String _cap(String s) => s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}';

/// Format an ISO date string as "Jan 1, 2026".
String _fmtDate(String iso) {
  const months = ['Jan','Feb','Mar','Apr','May','Jun',
                   'Jul','Aug','Sep','Oct','Nov','Dec'];
  try {
    final d = DateTime.parse(iso);
    return '${months[d.month-1]} ${d.day}, ${d.year}';
  } catch (_) { return iso; }
}