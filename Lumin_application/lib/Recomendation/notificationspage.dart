import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  int _tab = 0; // 0=recommendations, 1=bill limit, 2=solar forecast

  // Demo data (عدّليها لاحقاً حسب بياناتك)
  final List<_NotifItem> _recs = const [
    _NotifItem(
      title: 'Run the washing machine now',
      subtitle: 'Suggested • Now',
      body: 'Solar production is high. Running it now can reduce grid usage and cost.',
      icon: Icons.flash_on_rounded,
      accent: AppColors.mint,
    ),
    _NotifItem(
      title: 'Lower AC by 1°C for 2 hours',
      subtitle: 'Suggested • Today',
      body: 'Peak consumption detected. A small adjustment can reduce demand with minimal comfort impact.',
      icon: Icons.ac_unit_rounded,
      accent: AppColors.mint,
    ),
  ];

  final List<_NotifItem> _bill = const [
    _NotifItem(
      title: 'You reached 80% of your bill limit',
      subtitle: 'Bill limit • Today',
      body: 'Consumption is approaching your monthly target. Consider reducing AC usage during peak hours.',
      icon: Icons.warning_amber_rounded,
      accent: Color(0xFFFFC56B),
    ),
    _NotifItem(
      title: 'Over-limit alert is enabled',
      subtitle: 'Bill limit • 2 days ago',
      body: 'We will notify you if your predicted bill exceeds your limit.',
      icon: Icons.notifications_active_rounded,
      accent: Color(0xFFFFC56B),
    ),
  ];

  final List<_NotifItem> _solar = const [
    _NotifItem(
      title: 'Weather may reduce solar production by 15%',
      subtitle: 'Solar forecast • Tomorrow',
      body: 'Partly cloudy conditions expected. Consider shifting heavy loads to the best solar window.',
      icon: Icons.cloud_rounded,
      accent: Color(0xFFFFC56B),
    ),
    _NotifItem(
      title: 'Strong solar window at 2–4 PM',
      subtitle: 'Solar forecast • This week',
      body: 'Forecast shows higher production mid-day. Scheduling appliances then can reduce grid usage.',
      icon: Icons.wb_sunny_rounded,
      accent: AppColors.mint,
    ),
  ];

  List<_NotifItem> get _items {
    if (_tab == 1) return _bill;
    if (_tab == 2) return _solar;
    return _recs;
  }

  String get _emptyText {
    if (_tab == 1) return 'No bill limit notifications right now.';
    if (_tab == 2) return 'No solar forecast notifications right now.';
    return 'No recommendations notifications right now.';
  }

  String get _sectionTitle {
    if (_tab == 1) return 'Bill Limit';
    if (_tab == 2) return 'Solar Forecast';
    return 'Recommendations';
  }

  @override
  Widget build(BuildContext context) {
    final items = _items;

    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Notifications',
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top filter (3 sections) — responsive لأن فيه scroll أفقي
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              child: Row(
                children: [
                  _FilterChip(
                    text: 'Recommendation',
                    selected: _tab == 0,
                    onTap: () => setState(() => _tab = 0),
                  ),
                  const SizedBox(width: 8),
                  _FilterChip(
                    text: 'Bill limit',
                    selected: _tab == 1,
                    onTap: () => setState(() => _tab = 1),
                  ),
                  const SizedBox(width: 8),
                  _FilterChip(
                    text: 'Solar forecast',
                    selected: _tab == 2,
                    onTap: () => setState(() => _tab = 2),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),

            Text(
              _sectionTitle,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w900,
                fontSize: 14.5,
              ),
            ),

            const SizedBox(height: 10),

            if (items.isEmpty)
              GlassCard(
                radius: 18,
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Icon(Icons.info_outline_rounded, color: Colors.white.withOpacity(0.65)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _emptyText,
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
              ...List.generate(items.length, (i) {
                final n = items[i];
                return Padding(
                  padding: EdgeInsets.only(bottom: i == items.length - 1 ? 0 : 10),
                  child: _NotifCard(item: n),
                );
              }),

            const SizedBox(height: 18),
          ],
        ),
      ),
    );
  }
}

class _NotifItem {
  final String title;
  final String subtitle;
  final String body;
  final IconData icon;
  final Color accent;

  const _NotifItem({
    required this.title,
    required this.subtitle,
    required this.body,
    required this.icon,
    required this.accent,
  });
}

class _NotifCard extends StatelessWidget {
  final _NotifItem item;

  const _NotifCard({required this.item});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      radius: 20,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Text(item.subtitle, style: const TextStyle(fontSize: 12, color: AppColors.sub)),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: item.accent.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(item.icon, color: item.accent, size: 18),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            item.body,
            style: const TextStyle(fontSize: 12, color: AppColors.sub, height: 1.25),
          ),
        ],
      ),
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