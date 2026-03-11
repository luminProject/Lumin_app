import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/theme/app_colors.dart';

class BillPredictionPage extends StatefulWidget {
  const BillPredictionPage({super.key});

  @override
  State<BillPredictionPage> createState() => _BillPredictionPageState();
}

class _BillPredictionPageState extends State<BillPredictionPage> {
  double? _billLimit;
  bool _overLimitAlert = true;

  // Mock data — اربطيها لاحقًا بالـ backend
  double _currentBill = 286;
  double _predictedBill = 480;
  double _currentUsage = 1142;
  double _predictedUsage = 1920;

  int _daysPassed = 11;
  int _daysInMonth = 31;
  DateTime _lastUpdated = DateTime.now();

  final TextEditingController _billLimitController = TextEditingController();

  @override
  void dispose() {
    _billLimitController.dispose();
    super.dispose();
  }

  bool get _hasBillLimit => _billLimit != null;

  double get _differenceFromLimit {
    if (_billLimit == null) return 0;
    return _predictedBill - _billLimit!;
  }

  bool get _isOverLimit {
    if (_billLimit == null) return false;
    return _predictedBill > _billLimit!;
  }

  double get _remainingToLimit {
    if (_billLimit == null) return 0;
    final value = _billLimit! - _predictedBill;
    return value < 0 ? 0 : value;
  }

  double get _forecastRatioRaw {
    if (_billLimit == null || _billLimit! <= 0) return 0;
    return _predictedBill / _billLimit!;
  }

  String get _monthLabel => 'March 2026';

  String get _formattedUpdatedTime {
    final hour = _lastUpdated.hour > 12
        ? _lastUpdated.hour - 12
        : (_lastUpdated.hour == 0 ? 12 : _lastUpdated.hour);
    final minute = _lastUpdated.minute.toString().padLeft(2, '0');
    final period = _lastUpdated.hour >= 12 ? 'PM' : 'AM';
    return '$hour:$minute $period';
  }

  String get _statusText {
    if (!_hasBillLimit) {
      return 'Set a monthly bill limit to compare your forecast against your budget.';
    }

    if (_isOverLimit) {
      return 'You may exceed your limit by ${_differenceFromLimit.round()} ﷼';
    }

    return 'You are on track to stay ${_remainingToLimit.round()} ﷼ below your limit';
  }

  void _openSetBillLimitSheet() {
    _billLimitController.text = _billLimit?.round().toString() ?? '';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1C2B2D),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (ctx) {
        return Container(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          decoration: const BoxDecoration(
            color: Color(0xFF1C2B2D),
            borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _hasBillLimit ? 'Adjust Bill Limit' : 'Set Bill Limit',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                  fontSize: 16,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                'Enter your monthly bill limit (﷼)',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.70),
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _billLimitController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
                cursorColor: Colors.white,
                decoration: InputDecoration(
                  hintText: 'e.g. 450',
                  hintStyle: TextStyle(color: Colors.white.withOpacity(0.35)),
                  filled: true,
                  fillColor: Colors.white.withOpacity(0.08),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide(color: Colors.white.withOpacity(0.10)),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide(color: Colors.white.withOpacity(0.10)),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide(color: Colors.white.withOpacity(0.25)),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: () {
                    final raw = _billLimitController.text.trim();
                    final value = double.tryParse(raw);
                    if (value == null || value <= 0) return;

                    setState(() {
                      _billLimit = value;
                      _lastUpdated = DateTime.now();
                    });

                    Navigator.pop(ctx);
                  },
                  child: Text(
                    _hasBillLimit ? 'Save Changes' : 'Set Bill Limit',
                    style: const TextStyle(
                      fontSize: 15.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Bill Prediction',
        actions: [
          IconButton(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const NotificationsPage()),
              );
            },
            icon: const Icon(
              Icons.notifications_none_rounded,
              color: AppColors.mint,
            ),
          ),
        ],
        bottomNavigationBar: const HomeBottomNav(currentIndex: 1),
        child: SingleChildScrollView(
          padding: const EdgeInsets.only(bottom: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 26),

              _buildForecastHeader(),
              const SizedBox(height: 14),

              _buildHeroForecastCard(),
              const SizedBox(height: 14),

              _buildDoubleStatCard(
                title: 'Bill Summary',
                leadingIcon: Icons.receipt_long_rounded,
                leftLabel: 'Current Bill',
                leftValue: _currentBill.round().toString(),
                leftUnit: '﷼ so far',
                rightLabel: 'Predicted Bill',
                rightValue: _predictedBill.round().toString(),
                rightUnit: '﷼ by month-end',
              ),
              const SizedBox(height: 12),

              _buildDoubleStatCard(
                title: 'Usage Summary',
                leadingIcon: Icons.flash_on_rounded,
                leftLabel: 'Current Usage',
                leftValue: _currentUsage.round().toString(),
                leftUnit: 'kWh so far',
                rightLabel: 'Predicted Usage',
                rightValue: _predictedUsage.round().toString(),
                rightUnit: 'kWh forecast',
              ),
              const SizedBox(height: 14),

              _buildAlertCard(),

              if (_hasBillLimit) ...[
                const SizedBox(height: 14),
                _buildLimitCard(),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildForecastHeader() {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.mint.withOpacity(0.16),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.insights_rounded,
              color: AppColors.mint,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Monthly Forecast',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14.5,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Forecast for $_monthLabel • based on $_daysPassed of $_daysInMonth days',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.68),
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeroForecastCard() {
    final Color ringColor = _hasBillLimit
        ? (_isOverLimit ? const Color(0xFFFF5A5F) : AppColors.mint)
        : Colors.white.withOpacity(0.28);

    final Color valueColor = _hasBillLimit
        ? (_isOverLimit ? const Color(0xFFFF5A5F) : AppColors.mint)
        : AppColors.mint;

    final double progressForCircle =
        _hasBillLimit ? _forecastRatioRaw.clamp(0.0, 1.0) : 0.0;

    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 20),
      radius: 22,
      child: Column(
        children: [
          const Text(
            'Predicted Monthly Bill',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 18),
          Center(
            child: SizedBox(
              width: 200,
              height: 200,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CustomPaint(
                    size: const Size(200, 200),
                    painter: CircularForecastPainter(
                      progress: progressForCircle,
                      color: ringColor,
                      backgroundColor: Colors.white.withOpacity(0.08),
                    ),
                  ),
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        '${_predictedBill.round()}',
                        style: TextStyle(
                          color: valueColor,
                          fontSize: 40,
                          fontWeight: FontWeight.w900,
                          height: 1,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'SAR',
                        style: TextStyle(
                          color: valueColor,
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        _hasBillLimit
                            ? 'vs Limit ${_billLimit!.round()} SAR'
                            : 'No bill limit set',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.65),
                          fontSize: 12.5,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            _statusText,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: _hasBillLimit && _isOverLimit
                  ? Colors.orangeAccent
                  : AppColors.mint,
              fontSize: 13,
              fontWeight: FontWeight.w800,
            ),
          ),
          if (!_hasBillLimit) ...[
            const SizedBox(height: 14),
            SizedBox(
              width: 180,
              height: 46,
              child: ElevatedButton(
                onPressed: _openSetBillLimitSheet,
                child: const Text(
                  'Set Bill Limit',
                  style: TextStyle(
                    fontSize: 14.5,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              _infoChip(
                icon: Icons.update_rounded,
                text: 'Updated at $_formattedUpdatedTime',
              ),
              _infoChip(
                icon: Icons.flash_on_rounded,
                text: '${_predictedUsage.round()} kWh',
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildDoubleStatCard({
    required String title,
    required IconData leadingIcon,
    required String leftLabel,
    required String leftValue,
    required String leftUnit,
    required String rightLabel,
    required String rightValue,
    required String rightUnit,
  }) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: AppColors.mint.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  leadingIcon,
                  color: AppColors.mint,
                  size: 18,
                ),
              ),
              const SizedBox(width: 12),
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14.5,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildStatColumn(
                  label: leftLabel,
                  value: leftValue,
                  unit: leftUnit,
                ),
              ),
              Container(
                width: 1,
                height: 58,
                color: Colors.white.withOpacity(0.08),
                margin: const EdgeInsets.symmetric(horizontal: 12),
              ),
              Expanded(
                child: _buildStatColumn(
                  label: rightLabel,
                  value: rightValue,
                  unit: rightUnit,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatColumn({
    required String label,
    required String value,
    required String unit,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: Colors.white.withOpacity(0.70),
            fontSize: 12,
            fontWeight: FontWeight.w700,
            height: 1.2,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w900,
            height: 1,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          unit,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: Colors.white.withOpacity(0.58),
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }

  Widget _buildAlertCard() {
    final bool enabled = _hasBillLimit;

    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      radius: 18,
      child: Opacity(
        opacity: enabled ? 1.0 : 0.55,
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                Icons.warning_amber_rounded,
                color: Colors.orange.withOpacity(0.95),
                size: 22,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Over-Limit Alert',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 14.5,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    enabled
                        ? 'Notify me if the forecast exceeds my monthly limit'
                        : 'Set a bill limit to enable over-limit alerts',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.62),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            Switch(
              value: enabled ? _overLimitAlert : false,
              activeThumbColor: AppColors.button,
              onChanged: enabled
                  ? (v) => setState(() => _overLimitAlert = v)
                  : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLimitCard() {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Monthly Bill Limit',
            style: TextStyle(
              color: Colors.white.withOpacity(0.80),
              fontSize: 13.5,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.06),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.08)),
            ),
            child: Text(
              '${_billLimit!.round()} ﷼',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              onPressed: _openSetBillLimitSheet,
              child: const Text(
                'Adjust Bill Limit',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _infoChip({
    required IconData icon,
    required String text,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 15,
            color: Colors.white.withOpacity(0.85),
          ),
          const SizedBox(width: 6),
          Text(
            text,
            style: TextStyle(
              color: Colors.white.withOpacity(0.82),
              fontSize: 11.2,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class CircularForecastPainter extends CustomPainter {
  final double progress;
  final Color color;
  final Color backgroundColor;

  CircularForecastPainter({
    required this.progress,
    required this.color,
    required this.backgroundColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final strokeWidth = 16.0;
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width / 2) - strokeWidth;

    final backgroundPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final progressPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    const startAngle = -math.pi / 2;
    const totalSweep = math.pi * 2;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      totalSweep,
      false,
      backgroundPaint,
    );

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      totalSweep * progress,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant CircularForecastPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.color != color ||
        oldDelegate.backgroundColor != backgroundColor;
  }
}