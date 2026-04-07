import 'dart:async';
import 'package:flutter/material.dart';
import 'package:lumin_application/Screens/devices/add_device_page.dart';
import 'package:lumin_application/Screens/devices/device_setup_page.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/device_card.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import 'package:lumin_application/Screens/home/home_page.dart';

// ✅ 1. استدعاء ملف الـ API
import 'package:lumin_application/services/api_service.dart';

class DeviceManagementPage extends StatefulWidget {
  const DeviceManagementPage({super.key});

  @override
  State<DeviceManagementPage> createState() => _DeviceManagementPageState();
}

class _DeviceManagementPageState extends State<DeviceManagementPage> {
  int _filter = 0; // 0=All, 1=Connected, 2=Disconnected

  // ✅ 2. حذفنا البيانات الوهمية، وجعلنا القائمة فارغة في البداية
  List<DeviceItem> _devices = [];
  List<dynamic> _rawDevicesData = [];

  // ✅ 3. متغيرات لحالة التحميل والخطأ
  bool _isLoading = true;
  String? _errorMessage;
  final ApiService _apiService = ApiService();
  Timer? _readingsRefreshTimer;

  @override
  void initState() {
    super.initState();
    _fetchDevicesFromApi(); // جلب البيانات أول ما تفتح الصفحة
    _readingsRefreshTimer = Timer.periodic(
      const Duration(minutes: 5),
      (_) => _fetchDevicesFromApi(),
    );
  }

  @override
  void dispose() {
    _readingsRefreshTimer?.cancel();
    super.dispose();
  }

  // ✅ 4. دالة جلب الأجهزة من الباك إند وتحويلها إلى شكل DeviceItem الخاص بكم
  Future<void> _fetchDevicesFromApi() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final data = await _apiService.getDevices();

      final List<DeviceItem> fetchedDevices = [];

      for (final json in data) {
        final int deviceId = json['device_id'];
        final String deviceType = (json['device_type'] ?? 'Unknown').toString();

        String latestValue = deviceType;

        try {
          final latestReading = await _apiService.getLatestReading(deviceId);
          final readingValue = latestReading?['kwh_value'];

          if (readingValue != null) {
            latestValue = '${readingValue.toString()} kW';
          } else if (deviceType == 'production') {
            final panelCapacity = json['panel_capacity'];
            if (panelCapacity != null &&
                panelCapacity.toString().trim().isNotEmpty) {
              latestValue = '${panelCapacity.toString()} W';
            }
          }
        } catch (_) {
          if (deviceType == 'production') {
            final panelCapacity = json['panel_capacity'];
            if (panelCapacity != null &&
                panelCapacity.toString().trim().isNotEmpty) {
              latestValue = '${panelCapacity.toString()} W';
            }
          }
        }

        fetchedDevices.add(
          DeviceItem(
            deviceId: deviceId,
            name: json['device_name'] ?? 'Unknown Device',
            value: latestValue,
            connected:
                true, // افتراضي لأن الباك إند حالياً لا يرسل حالة الاتصال
            running: true, // افتراضي
          ),
        );
      }

      if (mounted) {
        setState(() {
          _rawDevicesData = data;
          _devices = fetchedDevices;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  List<DeviceItem> get _filtered {
    return _devices.where((d) {
      if (_filter == 1) return d.connected;
      if (_filter == 2) return !d.connected;
      return true;
    }).toList();
  }

  Future<void> _applyDeviceEdits(
    DeviceItem d,
    Map<String, dynamic> updated,
  ) async {
    final updatedName = (updated['device_name'] ?? d.name).toString().trim();
    final updatedType = (updated['device_type'] ?? d.value).toString().trim();
    final updatedRoom = updated['room']?.toString();
    final updatedCapacity = (updated['panel_capacity'] ?? '').toString().trim();

    final updatedValue = updatedType == 'production'
        ? (updatedCapacity.isEmpty ? d.value : updatedCapacity)
        : updatedType;

    try {
      await _apiService.updateDeviceSettings(
        deviceId: d.deviceId,
        deviceName: updatedName.isEmpty ? d.name : updatedName,
        deviceType: updatedType,
        room: updatedType == 'production' ? null : updatedRoom,
        panelCapacity: updatedType == 'production' ? updatedCapacity : null,
      );

      setState(() {
        _devices = _devices.map((item) {
          if (item.deviceId == d.deviceId) {
            return item.copyWith(
              name: updatedName.isEmpty ? d.name : updatedName,
              value: updatedValue,
            );
          }
          return item;
        }).toList();
      });

      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Device settings updated')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to update device settings: $e')),
      );
    }
  }

  Future<void> _confirmDelete(DeviceItem d) async {
    // ✅ مهم: استخدمي context الحالي قبل أي pop
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0F1F2A),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          title: const Text(
            'Delete device?',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
          ),
          content: Text(
            'This will remove "${d.name}" from your devices list.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.75),
              fontWeight: FontWeight.w600,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: Text(
                'Cancel',
                style: TextStyle(color: Colors.white.withOpacity(0.70)),
              ),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFFF5A52),
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text(
                'Delete',
                style: TextStyle(fontWeight: FontWeight.w900),
              ),
            ),
          ],
        );
      },
    );

    if (result != true) return;
    if (!mounted) return;

    try {
      await _apiService.deleteDevice(d.deviceId);
      setState(() => _devices.remove(d));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Error deleting device'),
          backgroundColor: Colors.red,
        ),
      );
    }
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
          title: const Text(
            'Devices',
            style: TextStyle(fontWeight: FontWeight.w900),
          ),
          leading: IconButton(
            onPressed: () {
              Navigator.pushAndRemoveUntil(
                context,
                MaterialPageRoute(builder: (_) => const HomePage()),
                (route) => false,
              );
            },
            icon: const Icon(
              Icons.arrow_back_ios_new_rounded,
              color: Colors.white,
            ),
          ),
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
        ),

        // ✅ 5. عرض الواجهة بناءً على حالة التحميل
        body: SafeArea(
          // ✅ 6. تغليف القائمة بـ RefreshIndicator لتمكين السحب للتحديث
          child: RefreshIndicator(
            onRefresh: _fetchDevicesFromApi,
            color: AppColors.mint,
            backgroundColor: const Color(0xFF1C2B2D),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
              // لضمان عمل السحب للتحديث حتى لو كانت القائمة قصيرة
              physics: const AlwaysScrollableScrollPhysics(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 52), // compensate transparent appbar
                  if (_isLoading)
                    const Padding(
                      padding: EdgeInsets.only(bottom: 12),
                      child: Center(
                        child: CircularProgressIndicator(color: AppColors.mint),
                      ),
                    ),
                  if (_errorMessage != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: GlassCard(
                        radius: 18,
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.error_outline,
                              color: Colors.redAccent,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'Failed to load devices',
                                style: const TextStyle(color: Colors.white70),
                              ),
                            ),
                            TextButton(
                              onPressed: _fetchDevicesFromApi,
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      ),
                    ),

                  // ===== Stats =====
                  GlassCard(
                    radius: 18,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 14,
                    ),
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
                              MaterialPageRoute(
                                builder: (_) => const AddDevicePage(),
                              ),
                            ).then(
                              (_) => _fetchDevicesFromApi(),
                            ); // تحديث بعد الإضافة
                          },
                          icon: const Icon(Icons.add_rounded, size: 18),
                          label: const Text(
                            'Add',
                            style: TextStyle(fontWeight: FontWeight.w900),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.button,
                            elevation: 0,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
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
                          Icon(
                            Icons.info_outline_rounded,
                            color: Colors.white.withOpacity(0.65),
                          ),
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
                        padding: EdgeInsets.only(
                          bottom: i == filtered.length - 1 ? 0 : 10,
                        ),
                        // ✅ لم نقم بتغيير أي شيء في كرت الجهاز الخاص بكم
                        child: DeviceCard(
                          fullWidth: true,
                          title: d.name,
                          value: d.value,
                          active: d.connected,
                          running: d.running,
                          // onRename removed
                          onSettings: () async {
                            final originalDevice = _devices.firstWhere(
                              (item) => item.deviceId == d.deviceId,
                              orElse: () => d,
                            );

                            final rawDevice = _rawDevicesData.firstWhere(
                              (item) => item['device_id'] == d.deviceId,
                              orElse: () => {
                                'device_type': 'consumption',
                                'room': null,
                                'panel_capacity': null,
                              },
                            );

                            final isProduction =
                                rawDevice['device_type'] == 'production';

                            final result = await Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => DeviceSetupPage(
                                  deviceId: originalDevice.name,
                                  isEditMode: true,
                                  deviceDbId: d.deviceId,
                                  initialName: originalDevice.name,
                                  initialRoom: isProduction
                                      ? null
                                      : rawDevice['room']?.toString(),
                                  initialDeviceType: isProduction
                                      ? 'production'
                                      : 'consumption',
                                  initialPanelCapacity: isProduction
                                      ? rawDevice['panel_capacity']?.toString()
                                      : null,
                                ),
                              ),
                            );

                            if (!mounted ||
                                result == null ||
                                result is! Map<String, dynamic>) {
                              return;
                            }

                            await _applyDeviceEdits(d, result);
                          },
                          onDelete: () => _confirmDelete(d),
                        ),
                      );
                    }),

                  const SizedBox(
                    height: 100,
                  ), // ✅ مساحة كفاية عشان ما يختفي آخر كرت تحت الـ bottom nav
                ],
              ),
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
  final int deviceId;
  final String name;
  final String value;
  final bool connected;
  final bool running;

  const DeviceItem({
    required this.deviceId,
    required this.name,
    required this.value,
    required this.connected,
    required this.running,
  });

  DeviceItem copyWith({
    int? deviceId,
    String? name,
    String? value,
    bool? connected,
    bool? running,
  }) {
    return DeviceItem(
      deviceId: deviceId ?? this.deviceId,
      name: name ?? this.name,
      value: value ?? this.value,
      connected: connected ?? this.connected,
      running: running ?? this.running,
    );
  }
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
          border: Border.all(
            color: selected ? AppColors.mint.withOpacity(0.35) : Colors.white12,
          ),
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

  const _StatInline({required this.value, required this.label});

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
