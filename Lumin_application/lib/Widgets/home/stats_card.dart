import 'dart:math';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import 'glass_card.dart';

enum StatsRange { day, week, month, year }

class StatsCardExact extends StatefulWidget {
  const StatsCardExact({super.key});

  @override
  State<StatsCardExact> createState() => _StatsCardExactState();
}

class _StatsCardExactState extends State<StatsCardExact> {
  StatsRange _range = StatsRange.week;

  // اختيار الوقت حسب التاب
  DateTime _selectedDay = DateTime.now(); // Day
  DateTime _weekAnchor = DateTime.now(); // Week: أي يوم داخل الأسبوع
  int _selectedMonth = DateTime.now().month; // Month
  int _selectedMonthYear = DateTime.now().year; // Month
  int _selectedYear = DateTime.now().year; // Year

  @override
  Widget build(BuildContext context) {
    final data = _buildSeries(_range);

    return GlassCard(
      radius: 20,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: _StatsTabsPill(
              active: _range,
              onChanged: (r) => setState(() => _range = r),
            ),
          ),
          const SizedBox(height: 12),

          // ✅ Legend + Date picker في نفس الصف
          Row(
            children: [
              Expanded(
                child: Wrap(
                  spacing: 14,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: const [
                    _LegendDot(color: AppColors.mint, text: 'Solar Production'),
                    _LegendDot(color: AppColors.cyan, text: 'Grid Import'),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              _RangePickerButton(
                text: _rangeLabel(),
                onTap: _openPickerForCurrentRange,
              ),
            ],
          ),
          const SizedBox(height: 10),

          AnimatedSwitcher(
            duration: const Duration(milliseconds: 260),
            switchInCurve: Curves.easeOutCubic,
            switchOutCurve: Curves.easeInCubic,
            transitionBuilder: (child, anim) {
              return FadeTransition(
                opacity: anim,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0.02, 0.03),
                    end: Offset.zero,
                  ).animate(anim),
                  child: child,
                ),
              );
            },
            child: SizedBox(
              key: ValueKey(_range),
              height: 190,
              child: LineChart(
                LineChartData(
                  minX: data.minX,
                  maxX: data.maxX,
                  minY: 0,
                  maxY: data.maxY,
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: data.yInterval,
                    getDrawingHorizontalLine: (_) =>
                        FlLine(color: Colors.white10, strokeWidth: 1),
                  ),
                  borderData: FlBorderData(show: false),
                  titlesData: FlTitlesData(
                    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 46,
                        interval: data.yInterval,
                        getTitlesWidget: (v, meta) {
                          if (v == 0) return const SizedBox.shrink();
                          return Padding(
                            padding: const EdgeInsets.only(right: 6),
                            child: Text(
                              '${v.toInt()} kWh',
                              style: const TextStyle(fontSize: 10, color: AppColors.sub),
                            ),
                          );
                        },
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        interval: data.xLabelInterval,
                        getTitlesWidget: (v, meta) {
                          final label = data.xLabel(v);
                          if (label == null) return const SizedBox.shrink();
                          return Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              label,
                              style: const TextStyle(fontSize: 10.5, color: AppColors.sub),
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  lineBarsData: [
                    _line(color: AppColors.mint, spots: data.solar, fillOpacity: 0.18),
                    _line(color: AppColors.cyan, spots: data.grid, fillOpacity: 0.10),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ===============================
  // Label + Picker
  // ===============================

  String _rangeLabel() {
    switch (_range) {
      case StatsRange.day:
        return _isToday(_selectedDay) ? 'Today' : _fmtDate(_selectedDay);

      case StatsRange.week:
        final start = _startOfWeekSat(_weekAnchor);
        final end = start.add(const Duration(days: 6));
        return '${_fmtShort(start)} - ${_fmtShort(end)}';

      case StatsRange.month:
        return '${_monthName(_selectedMonth)} $_selectedMonthYear';

      case StatsRange.year:
        return '$_selectedYear';
    }
  }

  Future<void> _openPickerForCurrentRange() async {
    switch (_range) {
      case StatsRange.day:
        final picked = await _pickDate(initial: _selectedDay);
        if (picked != null) setState(() => _selectedDay = picked);
        break;

      case StatsRange.week:
        final picked = await _pickDate(initial: _weekAnchor);
        if (picked != null) setState(() => _weekAnchor = picked);
        break;

      case StatsRange.month:
        final res = await _pickMonthYear(
          initialMonth: _selectedMonth,
          initialYear: _selectedMonthYear,
        );
        if (res != null) {
          setState(() {
            _selectedMonth = res.$1;
            _selectedMonthYear = res.$2;
          });
        }
        break;

      case StatsRange.year:
        final y = await _pickYear(initialYear: _selectedYear);
        if (y != null) setState(() => _selectedYear = y);
        break;
    }
  }

  Future<DateTime?> _pickDate({required DateTime initial}) {
    final now = DateTime.now();
    return showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(now.year - 5, 1, 1),
      lastDate: DateTime(now.year + 5, 12, 31),
      helpText: 'Select date',
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.dark(
              primary: AppColors.mint,
              surface: Color(0xFF0B2F32),
              onSurface: Colors.white,
            ),
          ),
          child: child!,
        );
      },
    );
  }

  Future<(int, int)?> _pickMonthYear({
    required int initialMonth,
    required int initialYear,
  }) async {
    int m = initialMonth;
    int y = initialYear;

    return showDialog<(int, int)>(
      context: context,
      builder: (_) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0B2F32),
          title: const Text('Select month', style: TextStyle(color: Colors.white)),
          content: Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: m,
                  dropdownColor: const Color(0xFF0B2F32),
                  decoration: const InputDecoration(
                    labelText: 'Month',
                    labelStyle: TextStyle(color: Colors.white70),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: Colors.white24),
                    ),
                  ),
                  items: List.generate(
                    12,
                    (i) => DropdownMenuItem(
                      value: i + 1,
                      child: Text(_monthName(i + 1),
                          style: const TextStyle(color: Colors.white)),
                    ),
                  ),
                  onChanged: (v) => m = v ?? m,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: y,
                  dropdownColor: const Color(0xFF0B2F32),
                  decoration: const InputDecoration(
                    labelText: 'Year',
                    labelStyle: TextStyle(color: Colors.white70),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: Colors.white24),
                    ),
                  ),
                  items: List.generate(11, (i) {
                    final val = DateTime.now().year - 5 + i;
                    return DropdownMenuItem(
                      value: val,
                      child: Text('$val',
                          style: const TextStyle(color: Colors.white)),
                    );
                  }),
                  onChanged: (v) => y = v ?? y,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel', style: TextStyle(color: Colors.white70)),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, (m, y)),
              child: const Text('OK',
                  style: TextStyle(color: AppColors.mint, fontWeight: FontWeight.w800)),
            ),
          ],
        );
      },
    );
  }

  Future<int?> _pickYear({required int initialYear}) async {
    int y = initialYear;

    return showDialog<int>(
      context: context,
      builder: (_) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0B2F32),
          title: const Text('Select year', style: TextStyle(color: Colors.white)),
          content: DropdownButtonFormField<int>(
            value: y,
            dropdownColor: const Color(0xFF0B2F32),
            decoration: const InputDecoration(
              labelText: 'Year',
              labelStyle: TextStyle(color: Colors.white70),
              enabledBorder:
                  UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
            ),
            items: List.generate(21, (i) {
              final val = DateTime.now().year - 10 + i;
              return DropdownMenuItem(
                value: val,
                child: Text('$val', style: const TextStyle(color: Colors.white)),
              );
            }),
            onChanged: (v) => y = v ?? y,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel', style: TextStyle(color: Colors.white70)),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, y),
              child: const Text('OK',
                  style: TextStyle(color: AppColors.mint, fontWeight: FontWeight.w800)),
            ),
          ],
        );
      },
    );
  }

  // ===============================
  // Chart Data
  // ===============================

  LineChartBarData _line({
    required Color color,
    required List<FlSpot> spots,
    required double fillOpacity,
  }) {
    return LineChartBarData(
      isCurved: true,
      curveSmoothness: 0.35,
      barWidth: 3,
      color: color,
      dotData: const FlDotData(show: false),
      belowBarData: BarAreaData(show: true, color: color.withOpacity(fillOpacity)),
      spots: spots,
    );
  }

  _SeriesPack _buildSeries(StatsRange r) {
    switch (r) {
      case StatsRange.day:
        final xs = [0, 3, 6, 9, 12, 15, 18, 21, 24];
        final solar = <FlSpot>[];
        final grid = <FlSpot>[];
        for (final x in xs) {
          solar.add(FlSpot(x.toDouble(), _solarDayProfile(x.toDouble())));
          grid.add(FlSpot(x.toDouble(), _gridDayProfile(x.toDouble())));
        }
        final maxY = _niceMaxY(_maxY(solar, grid), stepHint: 5);
        return _SeriesPack(
          minX: 0,
          maxX: 24,
          maxY: maxY,
          yInterval: (maxY / 4).clamp(4, 10).roundToDouble(),
          xLabelInterval: 6,
          solar: solar,
          grid: grid,
          xLabel: (v) => (v.toInt() % 6 == 0) ? '${v.toInt()}h' : null,
        );

      case StatsRange.week:
        final solarVals = const [18, 21, 16, 24, 22, 19, 23];
        final gridVals = const [12, 10, 14, 9, 11, 13, 10];
        final solar = List.generate(7, (i) => FlSpot(i.toDouble(), solarVals[i].toDouble()));
        final grid = List.generate(7, (i) => FlSpot(i.toDouble(), gridVals[i].toDouble()));
        final maxY = _niceMaxY(_maxY(solar, grid), stepHint: 10);
        const labels = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

        return _SeriesPack(
          minX: 0,
          maxX: 6,
          maxY: maxY,
          yInterval: (maxY / 4).clamp(5, 15).roundToDouble(),
          xLabelInterval: 1,
          solar: solar,
          grid: grid,
          xLabel: (v) {
            final i = v.toInt();
            if (i < 0 || i > 6) return null;
            return labels[i];
          },
        );

      case StatsRange.month:
        final solarVals = const [420, 520, 610, 560];
        final gridVals = const [480, 430, 360, 410];
        final solar = List.generate(4, (i) => FlSpot(i.toDouble(), solarVals[i].toDouble()));
        final grid = List.generate(4, (i) => FlSpot(i.toDouble(), gridVals[i].toDouble()));
        final maxY = _niceMaxY(_maxY(solar, grid), stepHint: 50);

        return _SeriesPack(
          minX: 0,
          maxX: 3,
          maxY: maxY,
          yInterval: (maxY / 4).clamp(50, 200).roundToDouble(),
          xLabelInterval: 1,
          solar: solar,
          grid: grid,
          xLabel: (v) {
            final i = v.toInt();
            if (i < 0 || i > 3) return null;
            return 'W${i + 1}';
          },
        );

      case StatsRange.year:
        final base = _selectedYear;
        final bump = (base % 5) * 12;
        final solarVals = [
          420 + bump, 460 + bump, 520 + bump, 610 + bump, 680 + bump, 720 + bump,
          740 + bump, 700 + bump, 640 + bump, 580 + bump, 480 + bump, 430 + bump
        ];
        final gridVals = [
          520 + bump, 500 + bump, 470 + bump, 420 + bump, 360 + bump, 320 + bump,
          300 + bump, 310 + bump, 340 + bump, 390 + bump, 470 + bump, 510 + bump
        ];

        final solar = List.generate(12, (i) => FlSpot(i.toDouble(), solarVals[i].toDouble()));
        final grid = List.generate(12, (i) => FlSpot(i.toDouble(), gridVals[i].toDouble()));
        final maxY = _niceMaxY(_maxY(solar, grid), stepHint: 100);
        const labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

        return _SeriesPack(
          minX: 0,
          maxX: 11,
          maxY: maxY,
          yInterval: (maxY / 4).clamp(100, 250).roundToDouble(),
          xLabelInterval: 2,
          solar: solar,
          grid: grid,
          xLabel: (v) {
            final i = v.toInt();
            if (i < 0 || i > 11) return null;
            if (i % 2 != 0) return null;
            return labels[i];
          },
        );
    }
  }

  // ===============================
  // Helpers
  // ===============================

  bool _isToday(DateTime d) {
    final n = DateTime.now();
    return d.year == n.year && d.month == n.month && d.day == n.day;
  }

  String _fmtDate(DateTime d) => '${d.day}/${d.month}/${d.year}';
  String _fmtShort(DateTime d) => '${d.day}/${d.month}';

  String _monthName(int m) {
    const names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return names[(m - 1).clamp(0, 11)];
  }

  DateTime _startOfWeekSat(DateTime d) {
    final normalized = DateTime(d.year, d.month, d.day);
    final diff = (normalized.weekday - DateTime.saturday) % 7;
    return normalized.subtract(Duration(days: diff));
  }

  double _niceMaxY(double rawMax, {required double stepHint}) =>
      (rawMax / stepHint).ceil() * stepHint;

  double _maxY(List<FlSpot> a, List<FlSpot> b) {
    double m = 0;
    for (final s in a) {
      if (s.y > m) m = s.y;
    }
    for (final s in b) {
      if (s.y > m) m = s.y;
    }
    return m;
  }

  double _solarDayProfile(double hour) {
    final h = hour.clamp(0, 24);
    final peak = 13.0;
    final spread = 5.0;
    final val = 10 * exp(-pow((h - peak) / spread, 2));
    return (val * 0.9).clamp(0, 9.5);
  }

  double _gridDayProfile(double hour) {
    final h = hour.clamp(0, 24);
    final night = (h <= 6 || h >= 18) ? 6.0 : 3.0;
    final middayDip = 2.2 * exp(-pow((h - 13) / 4.5, 2));
    return (night - middayDip + 2.0).clamp(1.2, 8.5);
  }
}

class _SeriesPack {
  final double minX, maxX, maxY, yInterval, xLabelInterval;
  final List<FlSpot> solar;
  final List<FlSpot> grid;
  final String? Function(double x) xLabel;

  _SeriesPack({
    required this.minX,
    required this.maxX,
    required this.maxY,
    required this.yInterval,
    required this.xLabelInterval,
    required this.solar,
    required this.grid,
    required this.xLabel,
  });
}

// Tabs pill segmented
class _StatsTabsPill extends StatelessWidget {
  final StatsRange active;
  final ValueChanged<StatsRange> onChanged;

  const _StatsTabsPill({required this.active, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    Widget chip(String t, StatsRange r) {
      final isActive = r == active;
      return Expanded(
        child: GestureDetector(
          onTap: () => onChanged(r),
          behavior: HitTestBehavior.opaque,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOutCubic,
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color: isActive ? AppColors.mint.withOpacity(0.16) : Colors.transparent,
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: isActive ? AppColors.mint.withOpacity(0.30) : Colors.transparent,
              ),
            ),
            child: Center(
              child: AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeOutCubic,
                style: TextStyle(
                  fontSize: 12,
                  color: isActive ? AppColors.mint : AppColors.sub,
                  fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
                ),
                child: Text(t),
              ),
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.07),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withOpacity(0.10)),
      ),
      child: Row(
        children: [
          chip('Day', StatsRange.day),
          const SizedBox(width: 6),
          chip('Week', StatsRange.week),
          const SizedBox(width: 6),
          chip('Month', StatsRange.month),
          const SizedBox(width: 6),
          chip('Year', StatsRange.year),
        ],
      ),
    );
  }
}

// Date picker button
class _RangePickerButton extends StatelessWidget {
  final String text;
  final VoidCallback onTap;

  const _RangePickerButton({required this.text, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        constraints: const BoxConstraints(minHeight: 36),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: Colors.white.withOpacity(0.12)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.calendar_month_rounded, size: 16, color: Colors.white.withOpacity(0.75)),
            const SizedBox(width: 8),
            Text(
              text,
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w800,
                color: Colors.white.withOpacity(0.85),
              ),
            ),
            const SizedBox(width: 4),
            Icon(Icons.keyboard_arrow_down_rounded, size: 18, color: Colors.white.withOpacity(0.60)),
          ],
        ),
      ),
    );
  }
}

// Legend dot
class _LegendDot extends StatelessWidget {
  final Color color;
  final String text;

  const _LegendDot({required this.color, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(99),
            boxShadow: [BoxShadow(color: color.withOpacity(0.25), blurRadius: 10)],
          ),
        ),
        const SizedBox(width: 8),
        Text(text, style: const TextStyle(fontSize: 12, color: AppColors.sub)),
      ],
    );
  }
}
