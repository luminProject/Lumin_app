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
import 'package:lumin_application/Screens/profile settings page/edit_profile_page.dart';

class BillPredictionPage extends StatefulWidget {
  const BillPredictionPage({super.key});

  @override
  State<BillPredictionPage> createState() => _BillPredictionPageState();
}

class _BillPredictionPageState extends State<BillPredictionPage> {
  final ApiService _api = ApiService();

  double? _billLimit;
  bool _limitWarning = false;
  bool _forecastReady = false;

  bool _setupRequired = false;
  String? _setupMessage;
  String? _cycleStart;
  String? _cycleEnd;
  int _daysPassed = 0;

  double _currentBill = 0;
  double _predictedBill = 0;
  double _currentUsage = 0;
  double _predictedUsage = 0;

  DateTime _lastUpdated = DateTime.now();

  bool _isLoading = true;
  bool _isSaving = false;
  String? _errorMessage;

  Timer? _refreshTimer;
  final TextEditingController _billLimitController = TextEditingController();

  @override
  void initState() {
    super.initState();

    _loadBillData();

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

  bool get _hasBillLimit => _billLimit != null && _billLimit! > 0;

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

  String get _predictedBillRangeText {
    return _formatFixedRange(_predictedBill, 10, decimals: 0);
  }

  String get _predictedUsageRangeText {
    return _formatFixedRange(_predictedUsage, 100, decimals: 0);
  }

  double get _forecastRatioRaw {
    if (!_hasBillLimit || !_forecastReady || _billLimit! <= 0) return 0;
    return (_predictedBill + 10) / _billLimit!;
  }

  String get _formattedUpdatedTime {
    final hour = _lastUpdated.hour > 12
        ? _lastUpdated.hour - 12
        : (_lastUpdated.hour == 0 ? 12 : _lastUpdated.hour);
    final minute = _lastUpdated.minute.toString().padLeft(2, '0');
    final period = _lastUpdated.hour >= 12 ? 'PM' : 'AM';

    return '$hour:$minute $period';
  }

  String _formatDate(String date) {
    final d = DateTime.parse(date);

    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];

    return '${months[d.month - 1]} ${d.day}';
  }
    /// ✅ FIX Today Date
  String _formatDateTime(DateTime date) {
  // Force Saudi Arabia time UTC+3
  final d = DateTime.now().toUtc().add(const Duration(hours: 3));

  const months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];

  return '${months[d.month - 1]} ${d.day}';
}
  
  String? _calculateCycleEndFromStart(String? startDate) {
    if (startDate == null || startDate.isEmpty) return null;

    final start = DateTime.parse(startDate);
    final end = start.add(const Duration(days: 29));

    return end.toIso8601String().split('T').first;
  }

  String get _statusText {
    if (!_forecastReady) {
      return 'We need 7 days of data to estimate your bill.';
    }

    if (!_hasBillLimit) {
      return 'Set a bill limit to see if you are on track.';
    }

    if (_limitWarning) {
      return 'You may go over your limit.';
    }

    return 'You are on track and within your limit.';
  }

  void _showSuccessToast(String msg) {
    if (!mounted) return;

    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          backgroundColor: Colors.transparent,
          elevation: 0,
          duration: const Duration(milliseconds: 1600),
          margin: const EdgeInsets.fromLTRB(18, 0, 18, 18),
          content: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.mint.withOpacity(0.18),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: AppColors.mint.withOpacity(0.55),
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.check_circle,
                  color: AppColors.mint,
                  size: 18,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    msg,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
  }

  Future<void> _loadBillData({bool isAutoRefresh = false}) async {
    if (!mounted) return;

    if (!isAutoRefresh) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      final data = await _api.getBill();

      debugPrint('BILL RESPONSE: $data');

      final rawLimit = data['limit_amount'];
      final parsedLimit =
          rawLimit != null ? (rawLimit as num).toDouble() : null;

      final String? startFromBackend = data['cycle_start'];
      final String? endFromBackend = data['cycle_end'];

      if (!mounted) return;

      setState(() {
        _setupRequired = data['setup_required'] ?? false;
        _setupMessage = data['setup_message'];

        _cycleStart = startFromBackend;
        _cycleEnd =
            endFromBackend ?? _calculateCycleEndFromStart(startFromBackend);

        _daysPassed = ((data['days_passed'] ?? 0) as num).toInt();

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
        _errorMessage = null;
      });
    } catch (e) {
      debugPrint('BILL LOAD ERROR: $e');

      if (!mounted) return;

      if (!isAutoRefresh) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
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

  Future<void> _saveBillLimit(double limit) async {
    setState(() {
      _isSaving = true;
    });

    try {
      final data = await _api.setBillLimit(limit);

      debugPrint('BILL SAVE RESPONSE: $data');

      final rawLimit = data['limit_amount'];
      final parsedLimit =
          rawLimit != null ? (rawLimit as num).toDouble() : null;

      final String? startFromBackend = data['cycle_start'];
      final String? endFromBackend = data['cycle_end'];

      if (!mounted) return;

      setState(() {
        _setupRequired = data['setup_required'] ?? false;
        _setupMessage = data['setup_message'];

        _cycleStart = startFromBackend;
        _cycleEnd =
            endFromBackend ?? _calculateCycleEndFromStart(startFromBackend);

        _daysPassed = ((data['days_passed'] ?? 0) as num).toInt();

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
      _showSuccessToast('Bill limit updated successfully');
    } catch (e) {
      debugPrint('BILL SAVE ERROR: $e');
      rethrow;
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
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
                MaterialPageRoute(
                  builder: (_) => const NotificationsPage(),
                ),
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
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            _errorMessage!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.white),
                          ),
                          const SizedBox(height: 12),
                          ElevatedButton(
                            onPressed: _loadBillData,
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  )
                : _setupRequired
                    ? _buildSetupRequiredCard()
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: 10),
                          _buildForecastHeader(),
                          const SizedBox(height: 14),
                          _buildHeroForecastCard(),
                          const SizedBox(height: 14),
                          _buildDoubleStatCard(
                            title: 'Bill Summary',
                            leadingIcon: Icons.receipt_long_rounded,
                            leftLabel: 'Bill So Far',
                            leftValue: '${_currentBill.round()} ﷼',
                            leftUnit: 'based on your usage',
                            rightLabel: _forecastReady
                                ? 'Predicted Bill'
                                : 'Prediction Status',
                            rightValue: _forecastReady
                                ? '$_predictedBillRangeText ﷼'
                                : '--',
                            rightUnit: _forecastReady
                                ? 'by end of month'
                                : 'Need 7 days',
                          ),
                          const SizedBox(height: 12),
                          _buildDoubleStatCard(
                            title: 'Usage Summary',
                            leadingIcon: Icons.flash_on_rounded,
                            leftLabel: 'Usage So Far',
                            leftValue: _currentUsage.round().toString(),
                            leftUnit: 'kWh used until now',
                            rightLabel: 'Predicted Usage',
                            rightValue: _forecastReady
                                ? _predictedUsageRangeText
                                : '--',
                            rightUnit: _forecastReady
                                ? 'by end of month'
                                : 'Need 7 days',
                          ),
                          const SizedBox(height: 14),
                          _buildLimitCard(),
                          const SizedBox(height: 160),
                        ],
                      ),
      ),
    );
  }

  Widget _buildSetupRequiredCard() {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 26),
      radius: 24,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: AppColors.mint.withOpacity(0.16),
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: AppColors.mint.withOpacity(0.35),
              ),
            ),
            child: const Icon(
              Icons.calendar_month_rounded,
              color: AppColors.mint,
              size: 38,
            ),
          ),
          const SizedBox(height: 18),
          const Text(
            'Set Your Billing Date',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 21,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            _setupMessage ??
                'LUMIN needs your latest electricity bill end date to calculate your current billing cycle and show accurate bill predictions.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.72),
              fontSize: 13.5,
              fontWeight: FontWeight.w700,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.06),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: Colors.white.withOpacity(0.08),
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.info_outline_rounded,
                  color: AppColors.mint,
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'You can add it from your profile settings.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.75),
                      fontSize: 12.5,
                      fontWeight: FontWeight.w700,
                      height: 1.3,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              onPressed: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const EditProfilePage(),
                  ),
                );

                if (!mounted) return;
                _loadBillData();
              },
              icon: const Icon(Icons.edit_calendar_rounded, size: 20),
              label: const Text(
                'Set Billing Date',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                ),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF3F8E6B),
                foregroundColor: Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'After saving, come back here and your billing cycle will update automatically.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.48),
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
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
        String? sheetError;

        return StatefulBuilder(
          builder: (context, setSheetState) {
            final bool hasError = sheetError != null;

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
                    'Enter the maximum bill amount you want to stay under.',
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
                    onChanged: (_) {
                      if (sheetError != null) {
                        setSheetState(() {
                          sheetError = null;
                        });
                      }
                    },
                    decoration: InputDecoration(
                      hintText: 'e.g. 450 ﷼',
                      hintStyle: TextStyle(
                        color: Colors.white.withOpacity(0.35),
                      ),
                      filled: true,
                      fillColor: Colors.white.withOpacity(0.08),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide(
                          color: hasError
                              ? const Color(0xFFFF7A7A)
                              : Colors.white.withOpacity(0.10),
                        ),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide(
                          color: hasError
                              ? const Color(0xFFFF7A7A)
                              : Colors.white.withOpacity(0.10),
                        ),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide(
                          color: hasError
                              ? const Color(0xFFFF7A7A)
                              : Colors.white.withOpacity(0.25),
                          width: 1.2,
                        ),
                      ),
                    ),
                  ),
                  if (sheetError != null) ...[
                    const SizedBox(height: 10),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFF5A2328).withOpacity(0.45),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: const Color(0xFFFF7A7A).withOpacity(0.70),
                          width: 1.2,
                        ),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 22,
                            height: 22,
                            decoration: const BoxDecoration(
                              color: Color(0xFFFF7A7A),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.error_outline_rounded,
                              size: 14,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              sheetError!,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                                height: 1.3,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: ElevatedButton(
                      onPressed: () async {
                        if (_isSaving) return;

                        final text = _billLimitController.text.trim();

                        if (text.isEmpty) {
                          setSheetState(() {
                            sheetError = 'Please enter your bill limit.';
                          });
                          return;
                        }

                        final value = double.tryParse(text);

                        if (value == null) {
                          setSheetState(() {
                            sheetError = 'Bill limit must be a number.';
                          });
                          return;
                        }

                        if (value <= 0) {
                          setSheetState(() {
                            sheetError = 'Bill limit must be greater than 0.';
                          });
                          return;
                        }

                        setSheetState(() {
                          sheetError = null;
                        });

                        try {
                          await _saveBillLimit(value);
                        } catch (e) {
                          setSheetState(() {
                            sheetError =
                                e.toString().replaceFirst('Exception: ', '');
                          });
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF3F8E6B),
                        foregroundColor: Colors.white,
                        disabledBackgroundColor: const Color(0xFF3F8E6B),
                        disabledForegroundColor: Colors.white,
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: _isSaving
                          ? const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2.2,
                                    color: Colors.white,
                                  ),
                                ),
                                SizedBox(width: 10),
                                Text(
                                  'Saving...',
                                  style: TextStyle(
                                    fontSize: 15.5,
                                    fontWeight: FontWeight.w900,
                                    color: Colors.white,
                                  ),
                                ),
                              ],
                            )
                          : Text(
                              _hasBillLimit
                                  ? 'Save Changes'
                                  : 'Set Bill Limit',
                              style: const TextStyle(
                                fontSize: 15.5,
                                fontWeight: FontWeight.w900,
                                color: Colors.white,
                              ),
                            ),
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildForecastHeader() {
    final bool hasStart = _cycleStart != null && _cycleStart!.isNotEmpty;

    final String? calculatedEnd =
        hasStart ? _calculateCycleEndFromStart(_cycleStart!) : null;

    final String? displayEnd =
        (_cycleEnd != null && _cycleEnd!.isNotEmpty) ? _cycleEnd : calculatedEnd;

    final bool hasData = hasStart && displayEnd != null;

    final double progress =
        (_daysPassed > 0) ? (_daysPassed / 30).clamp(0.0, 1.0) : 0.0;

    return GlassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
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
              const Expanded(
                child: Text(
                  'Monthly Prediction',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            _forecastReady
                ? 'See your expected bill early and stay within your budget.'
                : 'Your prediction appears after 7 days of recorded usage.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.65),
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 20),
          if (hasData) ...[
            LayoutBuilder(
              builder: (context, constraints) {
                final width = constraints.maxWidth;

                double markerLeft = width * progress;

                const edgePadding = 42.0;
                if (markerLeft < edgePadding) markerLeft = edgePadding;
                if (markerLeft > width - edgePadding) {
                  markerLeft = width - edgePadding;
                }

                return Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          _formatDate(_cycleStart!),
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.7),
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Text(
                          _formatDate(displayEnd!),
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.7),
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Container(
                          height: 6,
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(20),
                          ),
                        ),
                        FractionallySizedBox(
                          widthFactor: progress,
                          child: Container(
                            height: 6,
                            decoration: BoxDecoration(
                              color: AppColors.mint,
                              borderRadius: BorderRadius.circular(20),
                            ),
                          ),
                        ),
                        Positioned(
                          left: markerLeft - 5,
                          top: -2,
                          child: Container(
                            width: 10,
                            height: 10,
                            decoration: const BoxDecoration(
                              color: AppColors.mint,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      height: 34,
                      child: Stack(
                        children: [
                          Positioned(
                            left: markerLeft - 26,
                            child: SizedBox(
                              width: 52,
                              child: Column(
                                children: [
                                  const Text(
                                    'Today',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      color: AppColors.mint,
                                      fontSize: 10,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    _formatDateTime(DateTime.now()),
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                      color: AppColors.mint,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                );
              },
            ),
          ] else ...[
            Text(
              'Billing period not available',
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ],
      ),
    );
  }

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

    final String billRangeText =
        _forecastReady ? _predictedBillRangeText.replaceAll('–', ' to ') : '--';

    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 20),
      radius: 22,
      child: Column(
        children: [
          const Text(
            'Your Predicted Bill',
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
                                'No prediction yet',
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

const SizedBox(height: 6),
          Text(
            _hasBillLimit
                ? 'Compared to your limit: ${_billLimit!.round()} ﷼'
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

  Widget _buildLimitCard() {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Bill Limit',
            style: TextStyle(
              color: Colors.white.withOpacity(0.80),
              fontSize: 13.5,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'We compare your estimated final bill with this limit.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.58),
              fontSize: 12,
              fontWeight: FontWeight.w600,
              height: 1.3,
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
              _hasBillLimit
                  ? '${_billLimit!.round()} ﷼'
                  : 'No bill limit has been set yet',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 46,
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