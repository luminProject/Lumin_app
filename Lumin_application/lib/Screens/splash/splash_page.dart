import 'dart:async';
import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter/material.dart';

import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Screens/login.dart';

class SplashPage extends StatefulWidget {
  const SplashPage({super.key});

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  late final Animation<double> _fadeIn;
  late final Animation<double> _scaleIn;
  late final Animation<double> _spotPulse; // spotlight تنفّس خفيف
  late final Animation<double> _shine; // shimmer position

  @override
  void initState() {
    super.initState();

    _c = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    );

    _fadeIn = CurvedAnimation(
      parent: _c,
      curve: const Interval(0.0, 0.45, curve: Curves.easeOutCubic),
    );

    _scaleIn = Tween<double>(begin: 0.96, end: 1.0).animate(
      CurvedAnimation(
        parent: _c,
        curve: const Interval(0.0, 0.55, curve: Curves.easeOutBack),
      ),
    );

    // spotlight نبضه بسيط جدًا
    _spotPulse = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.55, end: 1.0), weight: 55),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.70), weight: 45),
    ]).animate(
      CurvedAnimation(parent: _c, curve: Curves.easeInOutCubic),
    );

    // shimmer sweep: من -1 إلى +1 (يمر على اللوقو)
    _shine = Tween<double>(begin: -1.2, end: 1.2).animate(
      CurvedAnimation(
        parent: _c,
        curve: const Interval(0.25, 0.95, curve: Curves.easeInOutCubic),
      ),
    );

    _c.forward();

    // انتقلي للـ Login بعد لحظة
    Timer(const Duration(milliseconds: 1700), () {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const LoginPage()),
      );
    });
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GradientBackground(
        child: Stack(
          children: [
            // ✅ soft vignette
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: Alignment.topCenter,
                    radius: 1.15,
                    colors: [
                      Colors.white.withOpacity(0.05),
                      Colors.transparent,
                    ],
                    stops: const [0.0, 0.65],
                  ),
                ),
              ),
            ),

            // ✅ spotlight subtle (مو دائرة واضحة)
            Positioned.fill(
              child: AnimatedBuilder(
                animation: _c,
                builder: (_, __) {
                  final t = _spotPulse.value;
                  return Opacity(
                    opacity: 0.10 * t,
                    child: ImageFiltered(
                      imageFilter: ImageFilter.blur(
                        sigmaX: 40 + (t * 10),
                        sigmaY: 40 + (t * 10),
                      ),
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: RadialGradient(
                            center: const Alignment(0, -0.08),
                            radius: 0.85,
                            colors: [
                              AppColors.mint.withOpacity(0.30),
                              AppColors.cyan.withOpacity(0.14),
                              Colors.transparent,
                            ],
                            stops: const [0.0, 0.35, 1.0],
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),

            // ✅ Logo with premium shimmer
            Center(
              child: AnimatedBuilder(
                animation: _c,
                builder: (_, __) {
                  return Opacity(
                    opacity: _fadeIn.value,
                    child: Transform.scale(
                      scale: _scaleIn.value,
                      child: _LogoShimmer(
                        shineX: _shine.value,
                        child: Image.asset(
                          'assets/images/Lumin_logo.png',
                          width: 200,
                          fit: BoxFit.contain,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

///
/// لمعة احترافية تمر على اللوقو (Shimmer sweep)
/// - مو “فلتر” على كامل الشاشة
/// - بس ماسك اللوقو نفسه، فيطلع نظيف
///
class _LogoShimmer extends StatelessWidget {
  final double shineX; // -1.2 .. 1.2
  final Widget child;

  const _LogoShimmer({
    required this.shineX,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    // نستخدم ShaderMask: يخلي اللوقو يلمع بممر ضيق
    return Stack(
      alignment: Alignment.center,
      children: [
        // اللوقو الأصلي
        child,

        // طبقة اللمعة (مخففة جدًا)
        ShaderMask(
          shaderCallback: (Rect bounds) {
            final w = bounds.width;
            final x = (shineX * 0.5 + 0.5) * w; // map to 0..w تقريبًا
            final band = w * 0.22;

            return LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: [
                Colors.transparent,
                Colors.white.withOpacity(0.0),
                Colors.white.withOpacity(0.45),
                Colors.white.withOpacity(0.0),
                Colors.transparent,
              ],
              stops: [
                ((x - band) / w).clamp(0.0, 1.0),
                ((x - band * 0.35) / w).clamp(0.0, 1.0),
                (x / w).clamp(0.0, 1.0),
                ((x + band * 0.35) / w).clamp(0.0, 1.0),
                ((x + band) / w).clamp(0.0, 1.0),
              ],
            ).createShader(bounds);
          },
          blendMode: BlendMode.srcATop,
          child: Opacity(
            opacity: 0.50, // خفيف
            child: child,
          ),
        ),

        // glow بسيط جدًا حول اللوقو (يعطي depth بدون مبالغة)
        IgnorePointer(
          child: Opacity(
            opacity: 0.12,
            child: ImageFiltered(
              imageFilter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
              child: child,
            ),
          ),
        ),
      ],
    );
  }
}
