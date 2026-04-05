import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/services/api_service.dart';

class BillPredictionPage extends StatefulWidget {
  const BillPredictionPage({super.key});

  @override
  State<BillPredictionPage> createState() => _BillPredictionPageState();
}

class _BillPredictionPageState extends State<BillPredictionPage> {
  final ApiService _api = ApiService();

  // ---------------------------
  // DATA COMING FROM BACKEND
  // ---------------------------
  // These values are NOT calculated in Flutter.
  // They come ready from the backend endpoint: GET /bill/{user_id}
  double? _billLimit;
  bool _limitWarning = false;
  bool _forecastReady = false;

  double _currentBill = 0;
  double _predictedBill = 0;
  double _currentUsage = 0;
  double _predictedUsage = 0;

  // UI-only value:
  // We use this only to show the latest refresh time on screen.
  DateTime _lastUpdated = DateTime.now();

  // ---------------------------
  // UI STATE
  // ---------------------------
  bool _isLoading = true;
  bool _isSaving = false;
  String? _errorMessage;

  // Auto refresh timer for the page.
  Timer? _refreshTimer;

  // Controller for bill limit input field.
  final TextEditingController _billLimitController = TextEditingController();

  @override
  void initState() {
    super.initState();

    // Load data when page opens.
    _loadBillData();

    // Auto refresh every 30 seconds.
    // This refreshes displayed values from backend.
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (!mounted) return;
      _loadBillData(isAutoRefresh: true);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _billLimitController.dispose();
    super.dispose();
  }

  // True if the user already has a valid monthly bill limit.
  bool get _hasBillLimit => _billLimit != null && _billLimit! > 0;

  // ---------------------------
  // FRONTEND DISPLAY HELPERS
  // ---------------------------
  // Backend returns one predicted bill number and one predicted usage number.
  // In the UI, we show them as a small range for better presentation.
  // Example:
  // predicted bill  = 250  -> shown as 240–260
  // predicted usage = 900  -> shown as 800–1000
  //
  // This range is only for UI display.
  // It is NOT the actual forecast calculation.
  String _formatFixedRange(
    double centerValue,
    double halfRange, {
    int decimals = 0,
  }) {
    if (!_forecastReady || centerValue <= 0) return '--';

    final minValue = math.max(0, centerValue - halfRange);
    final maxValue = centerValue + halfRange;

    if (decimals == 0) {
      return '${minValue.round()}–${maxValue.round()}';
    }

    return '${minValue.toStringAsFixed(decimals)}–${maxValue.toStringAsFixed(decimals)}';
  }

  // Predicted bill range shown in UI only.
  String get _predictedBillRangeText {
    return _formatFixedRange(_predictedBill, 10, decimals: 0);
  }

  // Predicted usage range shown in UI only.
  String get _predictedUsageRangeText {
    return _formatFixedRange(_predictedUsage, 100, decimals: 0);
  }

  // Used for the circular progress ring.
  // This is only a visual ratio:
  // predicted bill / bill limit
  //
  // Example:
  // predicted = 200, limit = 400 => 0.5 progress
  double get _forecastRatioRaw {
    if (!_hasBillLimit || !_forecastReady || _billLimit! <= 0) return 0;
    return (_predictedBill + 10) / _billLimit!;
  }

  // Month label shown in header.
  String get _monthLabel {
    const months = <String>[
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    return '${months[_lastUpdated.month - 1]} ${_lastUpdated.year}';
  }

  // Time label shown as "Updated at ..."
  String get _formattedUpdatedTime {
    final hour = _lastUpdated.hour > 12
        ? _lastUpdated.hour - 12
        : (_lastUpdated.hour == 0 ? 12 : _lastUpdated.hour);
    final minute = _lastUpdated.minute.toString().padLeft(2, '0');
    final period = _lastUpdated.hour >= 12 ? 'PM' : 'AM';
    return '$hour:$minute $period';
  }

  // Status message shown under the main forecast circle.
  //
  // Important:
  // We do NOT re-calculate warning logic in frontend.
  // We trust the backend value: _limitWarning
  //
  // Why?
  // Because the backend is the source of truth for forecast logic.
  String get _statusText {
    if (!_forecastReady) {
      return 'Your first forecast will be available after 7 recorded days.';
    }

    if (!_hasBillLimit) {
      return 'Set a monthly bill limit to compare the forecast against your budget.';
    }

    if (_limitWarning) {
      return 'You are likely to exceed your limit';
    }

    return 'You are still within your limit';
  }

  // ---------------------------
  // LOAD BILL DATA FROM BACKEND
  // ---------------------------
  Future<void> _loadBillData({bool isAutoRefresh = false}) async {
    if (!mounted) return;

    // Show loading only for normal page load, not silent auto refresh.
    if (!isAutoRefresh) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      final data = await _api.getBill();

      final rawLimit = data['limit_amount'];
      final parsedLimit =
          rawLimit != null ? (rawLimit as num).toDouble() : null;

      if (!mounted) return;

      setState(() {
        // These values come directly from backend.
        _currentBill = ((data['actual_bill'] ?? 0) as num).toDouble();
        _predictedBill = ((data['predicted_bill'] ?? 0) as num).toDouble();
        _currentUsage = ((data['current_usage_kwh'] ?? 0) as num).toDouble();
        _predictedUsage =
            ((data['predicted_usage_kwh'] ?? 0) as num).toDouble();

        _billLimit =
            (parsedLimit != null && parsedLimit > 0) ? parsedLimit : null;

        // This warning is decided by backend.
        // Frontend only displays it.
        _limitWarning = data['limit_warning'] ?? false;

        // Forecast availability also comes from backend.
        _forecastReady = data['forecast_available'] ?? false;

        // UI refresh timestamp only.
        _lastUpdated = DateTime.now();

        _errorMessage = null;
      });
    } catch (e) {
      debugPrint('BILL LOAD ERROR: $e');

      if (!mounted) return;

      if (!isAutoRefresh) {
        setState(() {
          _errorMessage = 'Unable to load bill data';
        });
      }
    } finally {
      if (!mounted) return;

      if (!isAutoRefresh) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  // ---------------------------
  // SAVE MONTHLY BILL LIMIT
  // ---------------------------
  Future<void> _saveBillLimit(double limit) async {
    setState(() {
      _isSaving = true;
    });

    try {
      final data = await _api.setBillLimit(limit);

      final rawLimit = data['limit_amount'];
      final parsedLimit =
          rawLimit != null ? (rawLimit as num).toDouble() : null;

      if (!mounted) return;

      setState(() {
        // Refresh state from backend response after saving.
        _currentBill = ((data['actual_bill'] ?? 0) as num).toDouble();
        _predictedBill = ((data['predicted_bill'] ?? 0) as num).toDouble();
        _currentUsage = ((data['current_usage_kwh'] ?? 0) as num).toDouble();
        _predictedUsage =
            ((data['predicted_usage_kwh'] ?? 0) as num).toDouble();

        _billLimit =
            (parsedLimit != null && parsedLimit > 0) ? parsedLimit : null;

        _limitWarning = data['limit_warning'] ?? false;
        _forecastReady = data['forecast_available'] ?? false;
        _lastUpdated = DateTime.now();
      });

      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Bill limit updated successfully')),
      );
    } catch (e) {
      debugPrint('BILL SAVE ERROR: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to save bill limit')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  // ---------------------------
  // OPEN BOTTOM SHEET FOR BILL LIMIT
  // ---------------------------
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
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
                decoration: InputDecoration(
                  hintText: 'e.g. 450',
                  hintStyle: TextStyle(color: Colors.white.withOpacity(0.35)),
                  filled: true,
                  fillColor: Colors.white.withOpacity(0.08),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.10)),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.10)),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.25)),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _isSaving
                      ? null
                      : () {
                          final value =
                              double.tryParse(_billLimitController.text.trim());
                          if (value == null || value <= 0) return;
                          _saveBillLimit(value);
                        },
                  child: Text(
                    _isSaving
                        ? 'Saving...'
                        : (_hasBillLimit ? 'Save Changes' : 'Set Bill Limit'),
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
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _errorMessage != null
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          _errorMessage!,
                          style: const TextStyle(color: Colors.white),
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton(
                          onPressed: _loadBillData,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: _loadBillData,
                    child: SingleChildScrollView(
                      physics: const AlwaysScrollableScrollPhysics(),
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
                            leftValue: '${_currentBill.round()} ﷼',
                            leftUnit: 'so far',
                            rightLabel: _forecastReady
                                ? 'Predicted Bill'
                                : 'Forecast Status',
                            rightValue: _forecastReady
                                ? '$_predictedBillRangeText ﷼'
                                : '--',
                            rightUnit: _forecastReady
                                ? 'Expected by month-end'
                                : 'Need 7 days',
                          ),
                          const SizedBox(height: 12),
                          _buildDoubleStatCard(
                            title: 'Usage Summary',
                            leadingIcon: Icons.flash_on_rounded,
                            leftLabel: 'Current Usage',
                            leftValue: _currentUsage.round().toString(),
                            leftUnit: 'kWh so far',
                            rightLabel: 'Predicted Usage',
                            rightValue:
                                _forecastReady ? _predictedUsageRangeText : '--',
                            rightUnit: _forecastReady
                                ? 'Expected by month-end'
                                : 'Need 7 days',
                          ),
                          const SizedBox(height: 14),
                          _buildLimitCard(),
                        ],
                      ),
                    ),
                  ),
      ),
    );
  }

  // Top small header card.
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
                  _forecastReady
                      ? 'Forecast for $_monthLabel based on recent usage'
                      : 'Forecast will be available after 7 recorded days',
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

  // Main hero card with circle and status.
  Widget _buildHeroForecastCard() {
    final bool isWarning = _limitWarning;

    final Color ringColor = !_forecastReady
        ? Colors.white.withOpacity(0.20)
        : (_hasBillLimit
            ? (isWarning ? const Color(0xFFFF5A5F) : AppColors.mint)
            : Colors.white.withOpacity(0.28));

    final Color valueColor = !_forecastReady
        ? Colors.white70
        : (_hasBillLimit
            ? (isWarning ? const Color(0xFFFF5A5F) : AppColors.mint)
            : AppColors.mint);

    final double progressForCircle = (_hasBillLimit && _forecastReady)
        ? _forecastRatioRaw.clamp(0.0, 1.0)
        : 0.0;

    // Replace en dash with "to" so it fits the center text more clearly.
    final String billRangeText =
        _forecastReady ? _predictedBillRangeText.replaceAll('–', ' to ') : '--';

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
              width: 184,
              height: 184,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CustomPaint(
                    size: const Size(184, 184),
                    painter: CircularForecastPainter(
                      progress: progressForCircle,
                      color: ringColor,
                      backgroundColor: Colors.white.withOpacity(0.08),
                    ),
                  ),
                  SizedBox(
                    width: 118,
                    child: _forecastReady
                        ? Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                billRangeText,
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: valueColor,
                                  fontSize: 22,
                                  fontWeight: FontWeight.w900,
                                  height: 1.15,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                '﷼',
                                style: TextStyle(
                                  color: valueColor,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ],
                          )
                        : Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                '--',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: valueColor,
                                  fontSize: 30,
                                  fontWeight: FontWeight.w900,
                                  height: 1,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'No forecast yet',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: valueColor,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ],
                          ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Expected by month-end',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.65),
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            _hasBillLimit
                ? 'vs Limit ${_billLimit!.round()} ﷼'
                : 'No bill limit set',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.65),
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            _statusText,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: isWarning ? Colors.orangeAccent : AppColors.mint,
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
                text: _forecastReady
                    ? '$_predictedUsageRangeText kWh'
                    : 'Need 7 days',
              ),
            ],
          ),
        ],
      ),
    );
  }

  // Reusable double-stat card.
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

  // Card for showing and editing bill limit.
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
              _hasBillLimit ? '${_billLimit!.round()} ﷼' : 'Not set yet',
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
              child: Text(
                _hasBillLimit ? 'Adjust Bill Limit' : 'Set Bill Limit',
                style: const TextStyle(
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

  // Small reusable info chip.
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

// Custom painter for circular forecast ring.
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
    final strokeWidth = 12.0;
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

    // Background circle.
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      totalSweep,
      false,
      backgroundPaint,
    );

    // Progress circle.
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