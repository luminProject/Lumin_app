// ══════════════════════════════════════════════════════════════════
//  stats_card.dart
//
//  Home screen statistics chart — Solar Production vs Grid Import.
//  Data source: GET /stats/{userId}?range=week|month|year&anchor=...
//
//  Sprint 2 change: removed Day tab (energycalculation has one row/day,
//  no hourly granularity). Remaining tabs: Week | Month | Year.
// ══════════════════════════════════════════════════════════════════

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:lumin_application/services/api_service.dart';
import '../../theme/app_colors.dart';
import 'glass_card.dart';

// Day removed — no hourly data in energycalculation
enum StatsRange { week, month, year }

class StatsCardExact extends StatefulWidget {
  const StatsCardExact({super.key});

  @override
  State<StatsCardExact> createState() => _StatsCardExactState();
}

class _StatsCardExactState extends State<StatsCardExact> {
  final _api = ApiService();

  StatsRange _range = StatsRange.week;
  bool _loading = false;
  String? _error;

  // Date selection state per tab
  DateTime _weekAnchor        = DateTime.now();
  int      _selectedMonth     = DateTime.now().month;
  int      _selectedMonthYear = DateTime.now().year;
  int      _selectedYear      = DateTime.now().year;

  // Chart data from API — list of {x, solar, grid, label}
  List<Map<String, dynamic>> _points = [];

  @override
  void initState() {
    super.initState();
    _fetchStats();
  }

  // ── Build anchor string for the current tab ──────────────────────
  String _buildAnchor() {
    switch (_range) {
      case StatsRange.week:
        final d = _weekAnchor;
        return '${d.year}-${d.month.toString().padLeft(2,'0')}-${d.day.toString().padLeft(2,'0')}';
      case StatsRange.month:
        return '$_selectedMonthYear-${_selectedMonth.toString().padLeft(2,'0')}';
      case StatsRange.year:
        return '$_selectedYear';
    }
  }

  String _rangeParam() {
    switch (_range) {
      case StatsRange.week:  return 'week';
      case StatsRange.month: return 'month';
      case StatsRange.year:  return 'year';
    }
  }

  // ── Fetch from backend ───────────────────────────────────────────
  Future<void> _fetchStats() async {
    setState(() { _loading = true; _error = null; });
    try {
      final result = await _api.getStats(
        range: _rangeParam(),
        anchor: _buildAnchor(),
      );
      setState(() {
        _points = (result['points'] as List)
            .cast<Map<String, dynamic>>();
        _loading = false;
      });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  // ── Range label shown on the picker button ───────────────────────
  String _rangeLabel() {
    switch (_range) {
      case StatsRange.week:
        final start = _startOfWeekSat(_weekAnchor);
        final end   = start.add(const Duration(days: 6));
        return '${_fmtShort(start)} – ${_fmtShort(end)}';
      case StatsRange.month:
        return '${_monthName(_selectedMonth)} $_selectedMonthYear';
      case StatsRange.year:
        return '$_selectedYear';
    }
  }

  // ── Date picker dispatcher ───────────────────────────────────────
  Future<void> _openPickerForCurrentRange() async {
    switch (_range) {
      case StatsRange.week:
        final picked = await _pickDate(initial: _weekAnchor);
        if (picked != null) {
          setState(() => _weekAnchor = picked);
          _fetchStats();
        }
        break;
      case StatsRange.month:
        final res = await _pickMonthYear(
          initialMonth: _selectedMonth,
          initialYear:  _selectedMonthYear,
        );
        if (res != null) {
          setState(() {
            _selectedMonth     = res.$1;
            _selectedMonthYear = res.$2;
          });
          _fetchStats();
        }
        break;
      case StatsRange.year:
        final y = await _pickYear(initialYear: _selectedYear);
        if (y != null) {
          setState(() => _selectedYear = y);
          _fetchStats();
        }
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      radius: 20,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: _StatsTabsPill(
              active:    _range,
              onChanged: (r) {
                setState(() => _range = r);
                _fetchStats();
              },
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: Wrap(
                  spacing: 14, runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: const [
                    _LegendDot(color: AppColors.mint, text: 'Solar Production'),
                    _LegendDot(color: AppColors.cyan, text: 'Grid Import'),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              _RangePickerButton(
                text:  _rangeLabel(),
                onTap: _openPickerForCurrentRange,
              ),
            ],
          ),
          const SizedBox(height: 10),
          AnimatedSwitcher(
            duration:       const Duration(milliseconds: 260),
            switchInCurve:  Curves.easeOutCubic,
            switchOutCurve: Curves.easeInCubic,
            transitionBuilder: (child, anim) => FadeTransition(
              opacity: anim,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0.02, 0.03),
                  end:   Offset.zero,
                ).animate(anim),
                child: child,
              ),
            ),
            child: SizedBox(
              key:    ValueKey('${_range}_${_buildAnchor()}'),
              height: 190,
              child:  _loading
                  ? const Center(child: CircularProgressIndicator(color: AppColors.mint))
                  : _error != null
                      ? _ErrorView(error: _error!, onRetry: _fetchStats)
                      : _points.isEmpty
                          ? const _EmptyView()
                          : _buildChart(),
            ),
          ),
        ],
      ),
    );
  }

  // ── Chart ────────────────────────────────────────────────────────
  Widget _buildChart() {
    final solar = _points
        .map((p) => FlSpot((p['x'] as num).toDouble(), (p['solar'] as num).toDouble()))
        .toList();
    final grid = _points
        .map((p) => FlSpot((p['x'] as num).toDouble(), (p['grid'] as num).toDouble()))
        .toList();

    final labels = {for (final p in _points) (p['x'] as num).toDouble(): p['label'] as String};
    final maxX    = _points.isNotEmpty ? (_points.last['x'] as num).toDouble() : 1.0;
    final rawMaxY = _maxY(solar, grid);
    final stepHint = _range == StatsRange.year ? 100.0 : _range == StatsRange.month ? 50.0 : 10.0;
    final maxY     = _niceMaxY(rawMaxY, stepHint: stepHint);
    final yInt     = (maxY / 4).clamp(stepHint, stepHint * 5).roundToDouble();
    final xInt     = _range == StatsRange.year ? 2.0 : 1.0;

    return LineChart(LineChartData(
      minX: 0, maxX: maxX, minY: 0, maxY: maxY,
      gridData: FlGridData(
        show: true, drawVerticalLine: false,
        horizontalInterval: yInt,
        getDrawingHorizontalLine: (_) => FlLine(color: Colors.white10, strokeWidth: 1),
      ),
      borderData: FlBorderData(show: false),
      titlesData: FlTitlesData(
        topTitles:   const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        leftTitles:  AxisTitles(
          sideTitles: SideTitles(
            showTitles: true, reservedSize: 46, interval: yInt,
            getTitlesWidget: (v, _) {
              if (v == 0) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(right: 6),
                child: Text('${v.toInt()} kWh',
                  style: const TextStyle(fontSize: 10, color: AppColors.sub)),
              );
            },
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true, interval: xInt,
            getTitlesWidget: (v, _) {
              // For year: only show even indices
              if (_range == StatsRange.year && v.toInt() % 2 != 0) {
                return const SizedBox.shrink();
              }
              final label = labels[v];
              if (label == null) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(label,
                  style: const TextStyle(fontSize: 10.5, color: AppColors.sub)),
              );
            },
          ),
        ),
      ),
      lineBarsData: [
        _line(color: AppColors.mint, spots: solar, fillOpacity: 0.18),
        _line(color: AppColors.cyan, spots: grid,  fillOpacity: 0.10),
      ],
    ));
  }

  LineChartBarData _line({
    required Color color,
    required List<FlSpot> spots,
    required double fillOpacity,
  }) => LineChartBarData(
    isCurved: true, curveSmoothness: 0.35, barWidth: 3, color: color,
    dotData: const FlDotData(show: false),
    belowBarData: BarAreaData(show: true, color: color.withOpacity(fillOpacity)),
    spots: spots,
  );

  // ── Date pickers ─────────────────────────────────────────────────

  Future<DateTime?> _pickDate({required DateTime initial}) =>
    showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(DateTime.now().year - 5, 1, 1),
      lastDate:  DateTime(DateTime.now().year + 1, 12, 31),
      builder:   (ctx, child) => Theme(
        data: Theme.of(ctx).copyWith(
          colorScheme: const ColorScheme.dark(
            primary: AppColors.mint,
            surface: Color(0xFF0B2F32),
            onSurface: Colors.white,
          ),
        ),
        child: child!,
      ),
    );

  Future<(int, int)?> _pickMonthYear({
    required int initialMonth,
    required int initialYear,
  }) async {
    int m = initialMonth, y = initialYear;
    return showDialog<(int, int)>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: const Color(0xFF0B2F32),
        title: const Text('Select month', style: TextStyle(color: Colors.white)),
        content: Row(children: [
          Expanded(child: DropdownButtonFormField<int>(
            initialValue: m,
            dropdownColor: const Color(0xFF0B2F32),
            decoration: const InputDecoration(
              labelText: 'Month', labelStyle: TextStyle(color: Colors.white70),
              enabledBorder: UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
            ),
            items: List.generate(12, (i) => DropdownMenuItem(
              value: i + 1,
              child: Text(_monthName(i + 1), style: const TextStyle(color: Colors.white)),
            )),
            onChanged: (v) => m = v ?? m,
          )),
          const SizedBox(width: 12),
          Expanded(child: DropdownButtonFormField<int>(
            initialValue: y,
            dropdownColor: const Color(0xFF0B2F32),
            decoration: const InputDecoration(
              labelText: 'Year', labelStyle: TextStyle(color: Colors.white70),
              enabledBorder: UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
            ),
            items: List.generate(6, (i) {
              final val = DateTime.now().year - 2 + i;
              return DropdownMenuItem(
                value: val,
                child: Text('$val', style: const TextStyle(color: Colors.white)),
              );
            }),
            onChanged: (v) => y = v ?? y,
          )),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context),
            child: const Text('Cancel', style: TextStyle(color: Colors.white70))),
          TextButton(onPressed: () => Navigator.pop(context, (m, y)),
            child: const Text('OK', style: TextStyle(color: AppColors.mint, fontWeight: FontWeight.w800))),
        ],
      ),
    );
  }

  Future<int?> _pickYear({required int initialYear}) async {
    int y = initialYear;
    return showDialog<int>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: const Color(0xFF0B2F32),
        title: const Text('Select year', style: TextStyle(color: Colors.white)),
        content: DropdownButtonFormField<int>(
          initialValue: y,
          dropdownColor: const Color(0xFF0B2F32),
          decoration: const InputDecoration(
            labelText: 'Year', labelStyle: TextStyle(color: Colors.white70),
            enabledBorder: UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
          ),
          items: List.generate(6, (i) {
            final val = DateTime.now().year - 2 + i;
            return DropdownMenuItem(
              value: val,
              child: Text('$val', style: const TextStyle(color: Colors.white)),
            );
          }),
          onChanged: (v) => y = v ?? y,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context),
            child: const Text('Cancel', style: TextStyle(color: Colors.white70))),
          TextButton(onPressed: () => Navigator.pop(context, y),
            child: const Text('OK', style: TextStyle(color: AppColors.mint, fontWeight: FontWeight.w800))),
        ],
      ),
    );
  }

  // ── Helpers ──────────────────────────────────────────────────────

  String _fmtShort(DateTime d) => '${d.day}/${d.month}';

  String _monthName(int m) {
    const n = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return n[(m - 1).clamp(0, 11)];
  }

  DateTime _startOfWeekSat(DateTime d) {
    final normalized = DateTime(d.year, d.month, d.day);
    final diff = (normalized.weekday - DateTime.saturday) % 7;
    return normalized.subtract(Duration(days: diff));
  }

  double _niceMaxY(double rawMax, {required double stepHint}) =>
      rawMax == 0 ? stepHint * 4 : (rawMax / stepHint).ceil() * stepHint;

  double _maxY(List<FlSpot> a, List<FlSpot> b) {
    double m = 0;
    for (final s in [...a, ...b]) { if (s.y > m) m = s.y; }
    return m;
  }
}

// ══════════════════════════════════════════════════════════════════
//  LOADING / ERROR / EMPTY STATES
// ══════════════════════════════════════════════════════════════════

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;
  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) => Column(
    mainAxisAlignment: MainAxisAlignment.center, children: [
      const Icon(Icons.error_outline_rounded, color: Color(0xFFFF5A52), size: 28),
      const SizedBox(height: 8),
      Text(error, style: const TextStyle(fontSize: 11, color: AppColors.sub),
        textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis),
      const SizedBox(height: 8),
      TextButton(onPressed: onRetry,
        child: const Text('Retry', style: TextStyle(color: AppColors.mint, fontWeight: FontWeight.w800))),
    ]);
}

class _EmptyView extends StatelessWidget {
  const _EmptyView();
  @override
  Widget build(BuildContext context) => const Center(
    child: Text('No data for this period.',
      style: TextStyle(fontSize: 12, color: AppColors.sub)));
}

// ══════════════════════════════════════════════════════════════════
//  TAB PILL
// ══════════════════════════════════════════════════════════════════

class _StatsTabsPill extends StatelessWidget {
  final StatsRange active;
  final ValueChanged<StatsRange> onChanged;
  const _StatsTabsPill({required this.active, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    Widget chip(String t, StatsRange r) {
      final isActive = r == active;
      return Expanded(child: GestureDetector(
        onTap: () => onChanged(r),
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220), curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isActive ? AppColors.mint.withOpacity(0.16) : Colors.transparent,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: isActive ? AppColors.mint.withOpacity(0.30) : Colors.transparent),
          ),
          child: Center(child: AnimatedDefaultTextStyle(
            duration: const Duration(milliseconds: 220), curve: Curves.easeOutCubic,
            style: TextStyle(
              fontSize: 12,
              color: isActive ? AppColors.mint : AppColors.sub,
              fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
            ),
            child: Text(t),
          )),
        ),
      ));
    }

    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.07),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withOpacity(0.10)),
      ),
      child: Row(children: [
        chip('Week',  StatsRange.week),
        const SizedBox(width: 6),
        chip('Month', StatsRange.month),
        const SizedBox(width: 6),
        chip('Year',  StatsRange.year),
      ]),
    );
  }
}

// ══════════════════════════════════════════════════════════════════
//  RANGE PICKER BUTTON
// ══════════════════════════════════════════════════════════════════

class _RangePickerButton extends StatelessWidget {
  final String text;
  final VoidCallback onTap;
  const _RangePickerButton({required this.text, required this.onTap});

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap, borderRadius: BorderRadius.circular(999),
    child: Container(
      constraints: const BoxConstraints(minHeight: 36),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.07),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.calendar_month_rounded, size: 16, color: Colors.white.withOpacity(0.75)),
        const SizedBox(width: 8),
        Text(text, style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800,
          color: Colors.white.withOpacity(0.85))),
        const SizedBox(width: 4),
        Icon(Icons.keyboard_arrow_down_rounded, size: 18, color: Colors.white.withOpacity(0.60)),
      ]),
    ),
  );
}

// ══════════════════════════════════════════════════════════════════
//  LEGEND DOT
// ══════════════════════════════════════════════════════════════════

class _LegendDot extends StatelessWidget {
  final Color color;
  final String text;
  const _LegendDot({required this.color, required this.text});

  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
    Container(width: 10, height: 10,
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(99),
        boxShadow: [BoxShadow(color: color.withOpacity(0.25), blurRadius: 10)])),
    const SizedBox(width: 8),
    Text(text, style: const TextStyle(fontSize: 12, color: AppColors.sub)),
  ]);
}