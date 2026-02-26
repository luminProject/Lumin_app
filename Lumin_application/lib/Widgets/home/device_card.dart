import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import 'glass_card.dart';

class DeviceCard extends StatelessWidget {
  final String title;
  final String value;
  final bool active;

  final bool running;
  final bool fullWidth;
  final VoidCallback? onMenu;
  final VoidCallback? onLink;

  final VoidCallback? onSettings;
  final VoidCallback? onDelete;

  const DeviceCard({
    super.key,
    required this.title,
    required this.value,
    required this.active,
    this.running = false,
    this.fullWidth = false,
    this.onMenu,
    this.onLink,
    this.onSettings,
    this.onDelete,
  });

  void _openMenuSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      barrierColor: Colors.black.withOpacity(0.45),
      builder: (_) {
        return _GlassMenuSheet(
          title: title,
          onSettings: () {
            Navigator.of(context).pop();
            onSettings?.call();
          },
          onDelete: () {
            Navigator.of(context).pop();
            onDelete?.call();
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final accent = active ? AppColors.mint : Colors.white54;

    return LayoutBuilder(
      builder: (context, c) {
        final w = c.maxWidth.isFinite ? c.maxWidth : 170.0;
        final hasFiniteH = c.maxHeight.isFinite && c.maxHeight > 0;
        final h = hasFiniteH ? c.maxHeight : 160.0;

        // ✅ scale حسب العرض (ثابت) + tight mode لما الكرت قصير
        final scale = (w / 170.0).clamp(0.78, 1.10);
        final isHomeTight = (!fullWidth && hasFiniteH && h <= 126.0);

        // ✅ شدّ كل شيء شوي إذا الكرت صغير جدًا
        final pad = (isHomeTight ? 10.0 : 14.0) * scale;
        final icon = (isHomeTight ? 32.0 : 36.0) * scale;

        final rowGap = (isHomeTight ? 4.0 : (fullWidth ? 10.0 : 7.0)) * scale;
        final titleGap = (isHomeTight ? 4.0 : (fullWidth ? 10.0 : 7.0)) * scale;

        final waveHeight = (fullWidth ? 34.0 : (isHomeTight ? 16.0 : 22.0)) * scale;
        final statusHeight = fullWidth ? (16.0 * scale) : 0.0;

        final valueFont = (isHomeTight ? 12.5 : 14.0) * scale;

        // ======= الجزء العلوي (مشترك)
        Widget headerRow() {
          return Row(
            children: [
              InkWell(
                onTap: onLink,
                borderRadius: BorderRadius.circular(12 * scale),
                child: Container(
                  width: icon,
                  height: icon,
                  decoration: BoxDecoration(
                    color: active ? AppColors.mint.withOpacity(0.18) : Colors.white10,
                    borderRadius: BorderRadius.circular(12 * scale),
                  ),
                  child: Icon(Icons.link, color: accent, size: 18 * scale),
                ),
              ),
              const Spacer(),
              InkWell(
                onTap: () {
                  if (onMenu != null) {
                    onMenu!.call();
                  } else {
                    _openMenuSheet(context);
                  }
                },
                borderRadius: BorderRadius.circular(12 * scale),
                child: Padding(
                  padding: EdgeInsets.all((isHomeTight ? 4 : 6) * scale),
                  child: Icon(Icons.more_horiz, color: Colors.white54, size: 22 * scale),
                ),
              ),
            ],
          );
        }

        Widget waveOrLine() {
          return SizedBox(
            height: waveHeight,
            width: double.infinity,
            child: active
                ? ClipRect(
                    child: CustomPaint(
                      painter: _WavePainter(
                        color: AppColors.mint.withOpacity(0.95),
                        strokeWidth: 2.6 * scale,
                      ),
                      child: const SizedBox.expand(),
                    ),
                  )
                : Align(
                    alignment: Alignment.center,
                    child: Container(
                      height: 1,
                      width: double.infinity,
                      color: Colors.white24,
                    ),
                  ),
          );
        }

        Widget valueWidget() {
          return Align(
            alignment: Alignment.centerRight,
            child: FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerRight,
              child: Text(
                value,
                style: TextStyle(
                  fontSize: valueFont,
                  fontWeight: FontWeight.w800,
                  color: active ? AppColors.mint : Colors.white38,
                ),
                maxLines: 1,
              ),
            ),
          );
        }

        // ✅ Layout A: للهوم (ارتفاع محدود) — نستخدم Expanded بأمان
        Widget homeLayout() {
          return Column(
            mainAxisSize: MainAxisSize.max,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              headerRow(),
              SizedBox(height: rowGap),

              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(fontSize: 14 * scale, fontWeight: FontWeight.w700),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    SizedBox(height: titleGap),
                    waveOrLine(),
                  ],
                ),
              ),

              valueWidget(),
            ],
          );
        }

        // ✅ Layout B: للـ fullWidth داخل Scroll (ارتفاع غير محدود) — بدون Expanded نهائيًا
        Widget fullWidthLayout() {
          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              headerRow(),
              SizedBox(height: rowGap),

              Text(
                title,
                style: TextStyle(fontSize: 14 * scale, fontWeight: FontWeight.w700),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),

              SizedBox(height: titleGap),
              waveOrLine(),

              SizedBox(height: 8 * scale),

              SizedBox(
                height: statusHeight,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    active ? (running ? 'Connected • Running' : 'Connected') : 'Disconnected',
                    style: TextStyle(
                      fontSize: 11 * scale,
                      fontWeight: FontWeight.w700,
                      color: active ? AppColors.mint : Colors.white38,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),

              SizedBox(height: 8 * scale),
              valueWidget(),
            ],
          );
        }

        final child = fullWidth
            ? fullWidthLayout()
            : (hasFiniteH ? homeLayout() : fullWidthLayout()); // fallback آمن

        return GlassCard(
          radius: 20,
          padding: EdgeInsets.all(pad),
          child: ClipRect( // ✅ يمنع أي بكسلات زيادة تسبب تحذير
            child: child,
          ),
        );
      },
    );
  }
}

class _GlassMenuSheet extends StatelessWidget {
  final String title;
  final VoidCallback onSettings;
  final VoidCallback onDelete;

  const _GlassMenuSheet({
    required this.title,
    required this.onSettings,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).padding.bottom;

    return SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.fromLTRB(16, 0, 16, 26 + bottomInset),
        child: Material(
          type: MaterialType.transparency,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(22),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(color: Colors.white12),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const SizedBox(height: 12),
                    Container(
                      width: 50,
                      height: 5,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.22),
                        borderRadius: BorderRadius.circular(99),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                                fontSize: 14.5,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    _menuTile(
                      icon: Icons.settings_rounded,
                      text: 'Device settings',
                      iconColor: Colors.white.withOpacity(0.85),
                      textColor: Colors.white.withOpacity(0.92),
                      trailing: Icons.chevron_right_rounded,
                      onTap: onSettings,
                      height: 56,
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Divider(color: Colors.white.withOpacity(0.12), height: 18),
                    ),
                    _menuTile(
                      icon: Icons.delete_rounded,
                      text: 'Delete',
                      iconColor: const Color(0xFFFF5A52),
                      textColor: const Color(0xFFFF5A52),
                      onTap: onDelete,
                      height: 56,
                    ),
                    const SizedBox(height: 14),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _menuTile({
    required IconData icon,
    required String text,
    required Color iconColor,
    required Color textColor,
    IconData? trailing,
    required VoidCallback onTap,
    double height = 52,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        child: Container(
          height: height,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.10)),
          ),
          child: Row(
            children: [
              Icon(icon, color: iconColor, size: 21),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  text,
                  style: TextStyle(color: textColor, fontWeight: FontWeight.w800),
                ),
              ),
              if (trailing != null)
                Icon(trailing, color: Colors.white.withOpacity(0.40), size: 22),
            ],
          ),
        ),
      ),
    );
  }
}

class _WavePainter extends CustomPainter {
  final Color color;
  final double strokeWidth;

  _WavePainter({required this.color, required this.strokeWidth});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final inset = strokeWidth / 2;
    final usableH = max(0.0, size.height - (inset * 2));
    final usableW = max(0.0, size.width - (inset * 2));

    final mid = inset + usableH * 0.58;
    final amp = usableH * 0.18;

    final path = Path()..moveTo(inset, mid);
    for (double x = 0; x <= usableW; x += 1) {
      final y = mid + sin(x / 10) * amp;
      path.lineTo(inset + x, y);
    }

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _WavePainter old) {
    return old.color != color || old.strokeWidth != strokeWidth;
  }
}
