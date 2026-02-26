import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import 'device_card.dart';

class DevicesSection extends StatefulWidget {
  final VoidCallback? onSeeAll;
  final double height;

  const DevicesSection({
    super.key,
    required this.height,
    this.onSeeAll,
  });

  @override
  State<DevicesSection> createState() => _DevicesSectionState();
}

class _DevicesSectionState extends State<DevicesSection> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 4, vsync: this);

  final Map<String, List<_DeviceItem>> roomDevices = const {
    'Living Room': [
      _DeviceItem('Living Room TV', '0.0 kW', false),
      _DeviceItem('Air Conditioning', '7.20 kW', true),
      _DeviceItem('Lamp', '0.12 kW', false),
      _DeviceItem('Speaker', '0.05 kW', false),
    ],
    'Kitchen': [
      _DeviceItem('Fridge', '0.30 kW', true),
      _DeviceItem('Oven', '1.80 kW', false),
      _DeviceItem('Microwave', '1.20 kW', false),
      _DeviceItem('Dishwasher', '0.90 kW', false),
    ],
    'Bedroom': [
      _DeviceItem('AC', '2.10 kW', true),
      _DeviceItem('Heater', '0.00 kW', false),
      _DeviceItem('Desk Lamp', '0.08 kW', false),
      _DeviceItem('TV', '0.15 kW', false),
    ],
    'Bathroom': [
      _DeviceItem('Water Heater', '2.40 kW', true),
      _DeviceItem('Vent Fan', '0.06 kW', false),
      _DeviceItem('Light', '0.03 kW', false),
    ],
  };

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final rooms = roomDevices.keys.toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text('Devices', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const Spacer(),
            InkWell(
              onTap: widget.onSeeAll,
              borderRadius: BorderRadius.circular(10),
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                child: Text('See all', style: TextStyle(color: AppColors.sub, fontSize: 12)),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),

        TabBar(
          controller: _tabs,
          isScrollable: true,
          indicatorColor: AppColors.mint,
          labelColor: AppColors.text,
          unselectedLabelColor: AppColors.sub,
          tabs: rooms.map((r) => Tab(text: r)).toList(),
        ),
        const SizedBox(height: 12),

        SizedBox(
          height: widget.height,
          child: TabBarView(
            controller: _tabs,
            children: rooms.map((roomName) {
              final devices = roomDevices[roomName] ?? const <_DeviceItem>[];
              return _RoomDevicesHorizontalList(devices: devices);
            }).toList(),
          ),
        ),
      ],
    );
  }
}

class _DeviceItem {
  final String title;
  final String value;
  final bool active;
  const _DeviceItem(this.title, this.value, this.active);
}

class _RoomDevicesHorizontalList extends StatelessWidget {
  final List<_DeviceItem> devices;
  const _RoomDevicesHorizontalList({required this.devices});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        const gap = 12.0;

        // ✅ يخلي كرتين يعبّون العرض (بدون فراغ يمين)
        final itemWidth = (constraints.maxWidth - gap) / 2;

        return ListView.separated(
          scrollDirection: Axis.horizontal,
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.only(bottom: 2),
          itemCount: devices.length,
          separatorBuilder: (_, __) => const SizedBox(width: gap),
          itemBuilder: (_, i) {
            final d = devices[i];
            return SizedBox(
              width: itemWidth,
              child: DeviceCard(
                title: d.title,
                value: d.value,
                active: d.active,
              ),
            );
          },
        );
      },
    );
  }
}
