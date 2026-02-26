import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';

// ✅ اربطيها بصفحتك الحقيقية
import 'package:lumin_application/Screens/devices/device_setup_page.dart';

class DeviceSearchPage extends StatefulWidget {
  const DeviceSearchPage({super.key});

  @override
  State<DeviceSearchPage> createState() => _DeviceSearchPageState();
}

class _DeviceSearchPageState extends State<DeviceSearchPage> {
  // Fake results (بدّليه لاحقاً بالبلوتوث الحقيقي)
  final List<String> _foundDevices = const [
    'SENSOR-AC-01',
    'SENSOR-AC-02',
    'SENSOR-AC-03',
    'SENSOR-AC-04',
  ];

  int? _selectedIndex;

  @override
  Widget build(BuildContext context) {
    final foundCount = _foundDevices.length;

    return GradientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        extendBody: true,
        extendBodyBehindAppBar: true,

        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          centerTitle: true,
          title: const Text(
            'Device Search',
            style: TextStyle(fontWeight: FontWeight.w900),
          ),
          leading: IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          ),
          actions: const [],
        ),

        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const SizedBox(height: 52), // compensate transparent appbar

                // ===== Top icon (loading-ish) =====
                Container(
                  width: 58,
                  height: 58,
                  decoration: BoxDecoration(
                    color: AppColors.mint.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: Colors.white12),
                  ),
                  child: const _SpinningIcon(
                    icon: Icons.autorenew_rounded,
                    size: 28,
                    color: AppColors.mint,
                  ),
                ),

                const SizedBox(height: 14),

                const Text(
                  'Search completed',
                  style: TextStyle(
                    fontSize: 15.5,
                    fontWeight: FontWeight.w900,
                  ),
                  textAlign: TextAlign.center,
                ),

                const SizedBox(height: 6),

                Text(
                  'Make sure Bluetooth is enabled on the device.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.70),
                    fontWeight: FontWeight.w700,
                    fontSize: 12.5,
                    height: 1.25,
                  ),
                  textAlign: TextAlign.center,
                ),

                const SizedBox(height: 14),

                Text(
                  'Found $foundCount devices',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontWeight: FontWeight.w800,
                    fontSize: 12.5,
                  ),
                ),

                const SizedBox(height: 12),

                // ===== List =====
                Column(
                  children: List.generate(_foundDevices.length, (i) {
                    final name = _foundDevices[i];
                    final selected = _selectedIndex == i;

                    return Padding(
                      padding: EdgeInsets.only(bottom: i == _foundDevices.length - 1 ? 0 : 10),
                      child: _SelectableDeviceTile(
                        name: name,
                        selected: selected,
                        onTap: () => setState(() => _selectedIndex = i),
                      ),
                    );
                  }),
                ),

                const SizedBox(height: 16),

                // ===== Buttons =====
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    onPressed: _selectedIndex == null
                        ? null
                        : () {
                            final selectedName = _foundDevices[_selectedIndex!];

                            // ✅ يروح مباشرة لصفحة الإعداد (بدون رجوع لصفحة البحث)
                            Navigator.pushReplacement(
                              context,
                              MaterialPageRoute(
                                builder: (_) => DeviceSetupPage(deviceId: selectedName),
                              ),
                            );
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.button,
                      disabledBackgroundColor: Colors.white10,
                      elevation: 0,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    ),
                    child: const Text(
                      'Continue',
                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15.5),
                    ),
                  ),
                ),

                const SizedBox(height: 10),

                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(color: Colors.white.withOpacity(0.18)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      backgroundColor: Colors.white.withOpacity(0.04),
                    ),
                    child: Text(
                      'Cancel',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.88),
                        fontWeight: FontWeight.w900,
                        fontSize: 15,
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 18),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SelectableDeviceTile extends StatelessWidget {
  final String name;
  final bool selected;
  final VoidCallback onTap;

  const _SelectableDeviceTile({
    required this.name,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: GlassCard(
        radius: 18,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            // ✅ icon LEFT
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: selected ? AppColors.mint.withOpacity(0.22) : Colors.white10,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white12),
              ),
              child: Icon(
                selected ? Icons.check_rounded : Icons.link_rounded,
                color: selected ? AppColors.mint : Colors.white54,
                size: 20,
              ),
            ),

            const SizedBox(width: 12),

            Expanded(
              child: Text(
                name,
                style: const TextStyle(fontWeight: FontWeight.w900),
              ),
            ),

            // ✅ radio indicator RIGHT
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: selected ? AppColors.mint : Colors.white24,
                  width: 2,
                ),
              ),
              child: Center(
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  width: selected ? 10 : 0,
                  height: selected ? 10 : 0,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.mint,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// ✅ أيقونة تدوّر (بدون أي باكجات)
class _SpinningIcon extends StatefulWidget {
  final IconData icon;
  final double size;
  final Color color;

  const _SpinningIcon({
    required this.icon,
    required this.size,
    required this.color,
  });

  @override
  State<_SpinningIcon> createState() => _SpinningIconState();
}

class _SpinningIconState extends State<_SpinningIcon> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 900))
        ..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RotationTransition(
      turns: _c,
      child: Icon(widget.icon, color: widget.color, size: widget.size),
    );
  }
}
