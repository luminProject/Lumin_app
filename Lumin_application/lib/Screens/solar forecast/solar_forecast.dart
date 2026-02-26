import 'package:flutter/material.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import 'package:lumin_application/Screens/bill_predection/bill_prediction.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/theme/app_colors.dart';

class SolarForecastPage extends StatelessWidget {
  const SolarForecastPage({super.key});

  @override
  Widget build(BuildContext context) {
    // بيانات تجريبية مثل اللي بالصورة
    final data = <double>[45, 52, 48, 60, 55, 66, 58];

    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Solar Forecast',
        leading: const SizedBox(width: 48), // نخلي العنوان بالوسط مثل الصورة
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
        bottomNavigationBar: const HomeBottomNav(currentIndex: 2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 6),

            // ===== Chart Card =====
            GlassCard(
              radius: 20,
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '7-Day Solar Production',
                    style: TextStyle(
                      fontSize: 14.5,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 14),

                  // الرسم
                  AspectRatio(
                    aspectRatio: 1.25, // قريب جدًا من شكل الصورة
                    child: _SolarLineChart(
                      values: data,
                      xLabels: const ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                      yMax: 70,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ===== Weather Impact Card (brown) =====
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF6B4E2E).withOpacity(0.55),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: Colors.white.withOpacity(0.06)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.cloud_rounded, color: Color(0xFFFFC56B), size: 22),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Weather Impact',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Partly cloudy tomorrow may reduce\nproduction by 15%',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.78),
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                            height: 1.25,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 18),

            // ===== Button =====
            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const BillPredictionPage()),
                  );
                },
                child: const Text(
                  'View Bill Prediction',
                  style: TextStyle(
                    fontSize: 15.5,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

/// رسم Line Chart بسيط بدون مكتبات خارجية
class _SolarLineChart extends StatelessWidget {
  final List<double> values;
  final List<String> xLabels;
  final double yMax;

  const _SolarLineChart({
    required this.values,
    required this.xLabels,
    required this.yMax,
  });

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _SolarLineChartPainter(
        values: values,
        xLabels: xLabels,
        yMax: yMax,
      ),
      child: const SizedBox.expand(),
    );
  }
}

class _SolarLineChartPainter extends CustomPainter {
  final List<double> values;
  final List<String> xLabels;
  final double yMax;

  _SolarLineChartPainter({
    required this.values,
    required this.xLabels,
    required this.yMax,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paddingLeft = 34.0;
    final paddingRight = 12.0;
    final paddingTop = 10.0;
    final paddingBottom = 26.0;

    final chartW = size.width - paddingLeft - paddingRight;
    final chartH = size.height - paddingTop - paddingBottom;

    final origin = Offset(paddingLeft, paddingTop);
    final chartRect = Rect.fromLTWH(origin.dx, origin.dy, chartW, chartH);

    // Grid paint
    final gridPaint = Paint()
      ..color = Colors.white.withOpacity(0.08)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    // Draw border
    canvas.drawRRect(
      RRect.fromRectAndRadius(chartRect, const Radius.circular(12)),
      gridPaint,
    );

    // Horizontal grid lines + y labels (0,20,40,60)
    final yTicks = <double>[0, 20, 40, 60];
    final textPainter = TextPainter(textDirection: TextDirection.ltr);

    for (final t in yTicks) {
      final y = origin.dy + chartH * (1 - (t / yMax));
      canvas.drawLine(Offset(origin.dx, y), Offset(origin.dx + chartW, y), gridPaint);

      // y label
      textPainter.text = TextSpan(
        text: t.toInt().toString(),
        style: TextStyle(
          color: Colors.white.withOpacity(0.55),
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(6, y - textPainter.height / 2));
    }

    // Vertical grid lines + x labels
    final n = values.length;
    for (int i = 0; i < n; i++) {
      final x = origin.dx + (chartW * i / (n - 1));
      canvas.drawLine(Offset(x, origin.dy), Offset(x, origin.dy + chartH), gridPaint);

      // x label
      if (i < xLabels.length) {
        textPainter.text = TextSpan(
          text: xLabels[i],
          style: TextStyle(
            color: Colors.white.withOpacity(0.6),
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        );
        textPainter.layout();
        textPainter.paint(
          canvas,
          Offset(x - textPainter.width / 2, origin.dy + chartH + 6),
        );
      }
    }

    // Convert values to points
    final points = <Offset>[];
    for (int i = 0; i < n; i++) {
      final vx = origin.dx + (chartW * i / (n - 1));
      final vy = origin.dy + chartH * (1 - (values[i] / yMax));
      points.add(Offset(vx, vy));
    }

    // Fill under line
    final fillPath = Path()..moveTo(points.first.dx, origin.dy + chartH);
    for (final p in points) {
      fillPath.lineTo(p.dx, p.dy);
    }
    fillPath.lineTo(points.last.dx, origin.dy + chartH);
    fillPath.close();

    final fillPaint = Paint()
      ..color = AppColors.mint.withOpacity(0.18)
      ..style = PaintingStyle.fill;

    canvas.drawPath(fillPath, fillPaint);

    // Line path
    final linePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (int i = 1; i < points.length; i++) {
      linePath.lineTo(points[i].dx, points[i].dy);
    }

    final linePaint = Paint()
      ..color = AppColors.mint.withOpacity(0.95)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    canvas.drawPath(linePath, linePaint);

    // Points dots
    final dotPaint = Paint()..color = AppColors.mint;
    for (final p in points) {
      canvas.drawCircle(p, 3.6, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _SolarLineChartPainter oldDelegate) {
    return oldDelegate.values != values || oldDelegate.yMax != yMax || oldDelegate.xLabels != xLabels;
  }
}
