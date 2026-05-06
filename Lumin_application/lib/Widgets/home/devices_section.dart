import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../theme/app_colors.dart';
import 'device_card.dart';

class DevicesSection extends StatefulWidget {
  final VoidCallback? onSeeAll;
  final double height;

  const DevicesSection({super.key, required this.height, this.onSeeAll});

  @override
  State<DevicesSection> createState() => _DevicesSectionState();
}

class _DevicesSectionState extends State<DevicesSection>
    with SingleTickerProviderStateMixin {
  final ApiService _apiService = ApiService();
  late Future<List<_DeviceItem>> _devicesFuture;
  TabController? _tabs;
  List<String> _currentRooms = const [];

  @override
  void initState() {
    super.initState();
    _devicesFuture = _loadDevices();
  }

  Future<List<_DeviceItem>> _loadDevices() async {
    final response = await _apiService.getDevices();

    return response
        .whereType<Map>()
        .map((device) => _DeviceItem.fromMap(Map<String, dynamic>.from(device)))
        .toList();
  }

  void _refreshDevices() {
    setState(() {
      _devicesFuture = _loadDevices();
    });
  }

  void _syncTabs(List<String> rooms) {
    final shouldRebuildTabs =
        _tabs == null ||
        _tabs!.length != rooms.length ||
        _currentRooms.join('|') != rooms.join('|');

    if (!shouldRebuildTabs) return;

    _tabs?.dispose();
    _currentRooms = rooms;
    _tabs = TabController(length: rooms.length, vsync: this);
  }

  Map<String, List<_DeviceItem>> _groupDevicesByRoom(
    List<_DeviceItem> devices,
  ) {
    final Map<String, List<_DeviceItem>> grouped = {
      'Living Room': <_DeviceItem>[],
      'Kitchen': <_DeviceItem>[],
      'Bedroom': <_DeviceItem>[],
      'Bathroom': <_DeviceItem>[],
      'Production': <_DeviceItem>[],
      'Other': <_DeviceItem>[],
    };

    for (final device in devices) {
      final room = _normalizeRoomName(device.room);
      grouped.putIfAbsent(room, () => []).add(device);
    }

    return grouped;
  }

  String _normalizeRoomName(String rawRoom) {
    final room = rawRoom.trim();
    if (room.isEmpty) return 'Other';

    final normalized = room.toLowerCase().replaceAll(RegExp(r'[^a-z]'), '');

    switch (normalized) {
      case 'livingroom':
      case 'living':
        return 'Living Room';
      case 'kitchen':
        return 'Kitchen';
      case 'bedroom':
      case 'bed':
        return 'Bedroom';
      case 'bathroom':
      case 'bath':
      case 'toilet':
      case 'restroom':
        return 'Bathroom';
      case 'production':
      case 'solar':
      case 'solarpanel':
        return 'Production';
      default:
        return room;
    }
  }

  @override
  void dispose() {
    _tabs?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              'Devices',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const Spacer(),
            IconButton(
              tooltip: 'Refresh devices',
              onPressed: _refreshDevices,
              icon: const Icon(
                Icons.refresh_rounded,
                color: AppColors.sub,
                size: 18,
              ),
            ),
            InkWell(
              onTap: widget.onSeeAll,
              borderRadius: BorderRadius.circular(10),
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                child: Text(
                  'See all',
                  style: TextStyle(color: AppColors.sub, fontSize: 12),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        FutureBuilder<List<_DeviceItem>>(
          future: _devicesFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return SizedBox(
                height: widget.height + 56,
                child: const Center(
                  child: CircularProgressIndicator(color: AppColors.mint),
                ),
              );
            }

            if (snapshot.hasError) {
              return _DevicesMessage(
                height: widget.height + 56,
                icon: Icons.wifi_off_rounded,
                title: 'Unable to load devices',
                subtitle: 'Check the backend connection, then refresh.',
                actionLabel: 'Retry',
                onAction: _refreshDevices,
              );
            }

            final devices = snapshot.data ?? const <_DeviceItem>[];
            if (devices.isEmpty) {
              return _DevicesMessage(
                height: widget.height + 56,
                icon: Icons.devices_other_rounded,
                title: 'No devices yet',
                subtitle:
                    'Added devices will appear here with their current reading.',
                actionLabel: 'Add device',
                onAction: widget.onSeeAll,
              );
            }

            final roomDevices = _groupDevicesByRoom(devices);
            final rooms = roomDevices.keys.toList();
            _syncTabs(rooms);

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TabBar(
                  controller: _tabs,
                  isScrollable: true,
                  indicatorColor: AppColors.mint,
                  labelColor: AppColors.text,
                  unselectedLabelColor: AppColors.sub,
                  tabs: rooms.map((room) => Tab(text: room)).toList(),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  height: widget.height,
                  child: TabBarView(
                    controller: _tabs,
                    children: rooms.map((roomName) {
                      final devices =
                          roomDevices[roomName] ?? const <_DeviceItem>[];
                      if (devices.isEmpty) {
                        return _EmptyRoomDevices(roomName: roomName);
                      }
                      return _RoomDevicesHorizontalList(devices: devices);
                    }).toList(),
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _DeviceItem {
  final String title;
  final String value;
  final bool active;
  final String room;

  const _DeviceItem({
    required this.title,
    required this.value,
    required this.active,
    required this.room,
  });

  factory _DeviceItem.fromMap(Map<String, dynamic> device) {
    final deviceType = (device['device_type'] ?? '').toString().toLowerCase();
    final isProduction = deviceType == 'production';

    final currentReading = isProduction
        ? _toDouble(device['production'])
        : _toDouble(device['consumption']);

    final title =
        (device['device_name'] ??
                device['name'] ??
                device['title'] ??
                'Unnamed Device')
            .toString();

    final room = isProduction
        ? 'Production'
        : (device['room'] ?? device['room_name'] ?? 'Other').toString();

    return _DeviceItem(
      title: title,
      value: '${currentReading.toStringAsFixed(2)} kW',
      active: currentReading > 0,
      room: room,
    );
  }

  static double _toDouble(dynamic value) {
    if (value == null) return 0;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString()) ?? 0;
  }
}

class _RoomDevicesHorizontalList extends StatelessWidget {
  final List<_DeviceItem> devices;
  const _RoomDevicesHorizontalList({required this.devices});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        const gap = 12.0;
        final itemWidth = (constraints.maxWidth - gap) / 2;

        return ListView.separated(
          scrollDirection: Axis.horizontal,
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.only(bottom: 2),
          itemCount: devices.length,
          separatorBuilder: (_, __) => const SizedBox(width: gap),
          itemBuilder: (_, i) {
            final device = devices[i];
            return SizedBox(
              width: itemWidth,
              child: DeviceCard(
                title: device.title,
                value: device.value,
                active: device.active,
              ),
            );
          },
        );
      },
    );
  }
}

class _EmptyRoomDevices extends StatelessWidget {
  final String roomName;

  const _EmptyRoomDevices({required this.roomName});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Center(
        child: Text(
          'No devices in $roomName yet',
          style: const TextStyle(
            color: AppColors.sub,
            fontWeight: FontWeight.w700,
            fontSize: 13,
          ),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

class _DevicesMessage extends StatelessWidget {
  final double height;
  final IconData icon;
  final String title;
  final String subtitle;
  final String actionLabel;
  final VoidCallback? onAction;

  const _DevicesMessage({
    required this.height,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: AppColors.sub, size: 28),
          const SizedBox(height: 10),
          Text(
            title,
            style: const TextStyle(
              color: AppColors.text,
              fontWeight: FontWeight.w800,
              fontSize: 14,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: const TextStyle(
              color: AppColors.sub,
              fontWeight: FontWeight.w500,
              fontSize: 12,
            ),
            textAlign: TextAlign.center,
          ),
          if (onAction != null) ...[
            const SizedBox(height: 12),
            TextButton(onPressed: onAction, child: Text(actionLabel)),
          ],
        ],
      ),
    );
  }
}
