import 'package:flutter/material.dart';
import 'package:lumin_application/Screens/devices/add_device_page.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/device_card.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';


class DeviceManagementPage extends StatefulWidget {
  const DeviceManagementPage({super.key});

  @override
  State<DeviceManagementPage> createState() => _DeviceManagementPageState();
}

class _DeviceManagementPageState extends State<DeviceManagementPage> {
  int _filter = 0; // 0=All, 1=Connected, 2=Disconnected

  final List<DeviceItem> _devices = [
    const DeviceItem(name: 'Master Bedroom AC', value: '34 kWh', connected: true, running: false),
    const DeviceItem(name: 'Living Room AC', value: '21 kWh', connected: true, running: true),
    const DeviceItem(name: 'Kitchen Fridge', value: '12 kWh', connected: true, running: true),
    const DeviceItem(name: 'Living Room TV', value: '0.0 kW', connected: false, running: false),
  ];

  List<DeviceItem> get _filtered {
    return _devices.where((d) {
      if (_filter == 1) return d.connected;
      if (_filter == 2) return !d.connected;
      return true;
    }).toList();
  }

  Future<void> _confirmDelete(DeviceItem d) async {
    // ✅ مهم: استخدمي context الحالي قبل أي pop
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0F1F2A),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          title: const Text(
            'Delete device?',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
          ),
          content: Text(
            'This will remove "${d.name}" from your devices list.',
            style: TextStyle(color: Colors.white.withOpacity(0.75), fontWeight: FontWeight.w600),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: Text('Cancel', style: TextStyle(color: Colors.white.withOpacity(0.70))),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFFF5A52),
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Delete', style: TextStyle(fontWeight: FontWeight.w900)),
            ),
          ],
        );
      },
    );

    if (result != true) return;
    if (!mounted) return;

    setState(() => _devices.remove(d));
  }

  @override
  Widget build(BuildContext context) {
    final connectedCount = _devices.where((d) => d.connected).length;
    final disconnectedCount = _devices.length - connectedCount;

    final filtered = _filtered;

    return GradientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        extendBody: true,
        extendBodyBehindAppBar: true,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          centerTitle: true,
          title: const Text('Devices', style: TextStyle(fontWeight: FontWeight.w900)),
          leading: IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          ),
          actions: [
            IconButton(
              onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const NotificationsPage()),
              );
            },
              icon: const Icon(Icons.notifications_none_rounded, color: AppColors.mint),
            ),
          ],
        ),

        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 52), // compensate transparent appbar

                // ===== Stats =====
                GlassCard(
                  radius: 18,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  child: Row(
                    children: [
                      Expanded(
                        child: _StatInline(
                          value: disconnectedCount.toString(),
                          label: 'Disconnected',
                        ),
                      ),
                      Container(
                        width: 1,
                        height: 44,
                        color: Colors.white.withOpacity(0.10),
                      ),
                      Expanded(
                        child: _StatInline(
                          value: connectedCount.toString(),
                          label: 'Connected',
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                // ===== Filters + Add (✅ no right overflow) =====
                Row(
                  children: [
                    Expanded(
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        physics: const BouncingScrollPhysics(),
                        child: Row(
                          children: [
                            _FilterChip(
                              text: 'All',
                              selected: _filter == 0,
                              onTap: () => setState(() => _filter = 0),
                            ),
                            const SizedBox(width: 8),
                            _FilterChip(
                              text: 'Connected',
                              selected: _filter == 1,
                              onTap: () => setState(() => _filter = 1),
                            ),
                            const SizedBox(width: 8),
                            _FilterChip(
                              text: 'Disconnected',
                              selected: _filter == 2,
                              onTap: () => setState(() => _filter = 2),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    SizedBox(
                      height: 38,
                      child: ElevatedButton.icon(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => const AddDevicePage()),
                          );
                        },
                        icon: const Icon(Icons.add_rounded, size: 18),
                        label: const Text('Add', style: TextStyle(fontWeight: FontWeight.w900)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.button,
                          elevation: 0,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                        ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 12),

                // ===== Devices list =====
                if (filtered.isEmpty)
                  GlassCard(
                    radius: 18,
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(Icons.info_outline_rounded, color: Colors.white.withOpacity(0.65)),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'No devices in this filter.',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.70),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  )
                else
                  ...List.generate(filtered.length, (i) {
                    final d = filtered[i];
                    return Padding(
                      padding: EdgeInsets.only(bottom: i == filtered.length - 1 ? 0 : 10),
                      child: DeviceCard(
                        fullWidth: true,
                        title: d.name,
                        value: d.value,
                        active: d.connected,
                        running: d.running,
                        // المنيو من الثلاث نقاط داخل الكارد
                        onSettings: () {
                          // روحي لصفحة إعدادات الجهاز عندك
                          // Navigator.push(context, MaterialPageRoute(builder: (_) => DeviceSetupPage(device: d)));
                        },
                        onDelete: () => _confirmDelete(d),
                      ),
                    );
                  }),

                const SizedBox(height: 100), // ✅ مساحة كفاية عشان ما يختفي آخر كرت تحت الـ bottom nav
              ],
            ),
          ),
        ),

        // ✅ مهم: استخدمي النسخة المعدلة من HomeBottomNav اللي تعالج overflow
        bottomNavigationBar: const HomeBottomNav(currentIndex: 3),
      ),
    );
  }
}

class DeviceItem {
  final String name;
  final String value;
  final bool connected;
  final bool running;

  const DeviceItem({
    required this.name,
    required this.value,
    required this.connected,
    required this.running,
  });
}

class _FilterChip extends StatelessWidget {
  final String text;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.text,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? AppColors.mint.withOpacity(0.18) : Colors.white10,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: selected ? AppColors.mint.withOpacity(0.35) : Colors.white12),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: selected ? AppColors.mint : Colors.white70,
            fontWeight: FontWeight.w800,
            fontSize: 12.5,
          ),
        ),
      ),
    );
  }
}

class _StatInline extends StatelessWidget {
  final String value;
  final String label;

  const _StatInline({
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w900,
            color: AppColors.mint,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.white.withOpacity(0.65),
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}