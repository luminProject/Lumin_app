import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';

class RecommendationsPage extends StatefulWidget {
  const RecommendationsPage({super.key});

  @override
  State<RecommendationsPage> createState() => _RecommendationsPageState();
}

class _RecommendationsPageState extends State<RecommendationsPage> {
  int _tab = 0; // 0 = New, 1 = History

  // History time filter (demo)
  String _timeFilter = 'Any time';

  final List<RecItem> _newRecs = const [
    RecItem(
      title: 'Run the washing machine now',
      subtitle: 'Suggested • Now',
      body:
          'Solar production is high (4.2 kW). Running it now can reduce grid usage and cost.',
      savingKwh: 1.2,
      savingSar: 15,
    ),
    RecItem(
      title: 'Lower AC by 1°C for 2 hours',
      subtitle: 'Suggested • Today',
      body:
          'Peak consumption detected. A small adjustment can reduce demand with minimal comfort impact.',
      savingKwh: 0.7,
      savingSar: 8,
    ),
    RecItem(
      title: 'Delay oven use to 2 PM',
      subtitle: 'Suggested • Later',
      body:
          'Solar output is expected to increase around 2 PM. Shifting heavy loads reduces grid dependency.',
      savingKwh: 0.9,
      savingSar: 10,
    ),
  ];

  final List<RecItem> _history = const [
    RecItem(
      title: 'Turn off idle TV standby',
      subtitle: '2 days ago',
      body:
          'Standby draw detected for long periods. Turning it off reduces wasted energy.',
      savingKwh: 0.2,
      savingSar: 2,
    ),
    RecItem(
      title: 'Schedule dishwasher after 1 PM',
      subtitle: '5 days ago',
      body:
          'Better solar window after 1 PM. Scheduling heavy loads helps reduce grid consumption.',
      savingKwh: 1.0,
      savingSar: 12,
    ),
    RecItem(
      title: 'Set bill limit alert to 80%',
      subtitle: '1 week ago',
      body:
          'An early alert helps you react before exceeding your target bill.',
      savingKwh: 0.0,
      savingSar: 0,
    ),
  ];

  List<RecItem> get _items {
    if (_tab == 0) return _newRecs;

    // time filter demo (بدون تاريخ فعلي)
    // لاحقًا: تربطينها بتاريخ/وقت وتصفّين فعليًا
    return _history;
  }

  @override
  Widget build(BuildContext context) {
    final items = _items;

    final newCount = _newRecs.length;
    final historyCount = _history.length;

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
            'Recommendations',
            style: TextStyle(fontWeight: FontWeight.w900),
          ),
          leading: IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          ),
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 52), // compensate transparent appbar

                // ✅ Counts on top ONLY
                GlassCard(
                  radius: 18,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  child: Row(
                    children: [
                      Expanded(
                        child: _StatInline(
                          value: newCount.toString(),
                          label: 'New',
                        ),
                      ),
                      Container(
                        width: 1,
                        height: 44,
                        color: Colors.white.withOpacity(0.10),
                      ),
                      Expanded(
                        child: _StatInline(
                          value: historyCount.toString(),
                          label: 'History',
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                // Tabs + Filter (Filter only for History)
                Row(
                  children: [
                    Expanded(
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        physics: const BouncingScrollPhysics(),
                        child: Row(
                          children: [
                            _FilterChip(
                              text: 'New',
                              selected: _tab == 0,
                              onTap: () => setState(() => _tab = 0),
                            ),
                            const SizedBox(width: 8),
                            _FilterChip(
                              text: 'History',
                              selected: _tab == 1,
                              onTap: () => setState(() => _tab = 1),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    if (_tab == 1)
                      SizedBox(
                        height: 38,
                        child: ElevatedButton.icon(
                          onPressed: _openTimeFilterSheet,
                          icon: const Icon(Icons.tune_rounded, size: 18),
                          label: const Text(
                            'Filter',
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

                // List
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
                            _tab == 0
                                ? 'No new recommendations right now.'
                                : 'No recommendations match this filter.',
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
                    final r = items[i];
                    return Padding(
                      padding: EdgeInsets.only(bottom: i == items.length - 1 ? 0 : 10),
                      child: _RecommendationCard(item: r),
                    );
                  }),

                const SizedBox(height: 30),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _openTimeFilterSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.5),
      isScrollControlled: true,
      builder: (_) {
        String time = _timeFilter;

        return Container(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          decoration: BoxDecoration(
            color: const Color(0xFF0F1F2A),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
            border: Border.all(color: Colors.white.withOpacity(0.08)),
          ),
          child: SafeArea(
            top: false,
            child: StatefulBuilder(
              builder: (ctx, setLocal) {
                return Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: Container(
                        width: 44,
                        height: 5,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.16),
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Filter history',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Colors.white),
                    ),
                    const SizedBox(height: 14),

                    Text(
                      'Time',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.white.withOpacity(0.65),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: ['Any time', 'Today', 'This week', 'This month']
                          .map(
                            (v) => _FilterChip(
                              text: v,
                              selected: time == v,
                              onTap: () => setLocal(() => time = v),
                            ),
                          )
                          .toList(),
                    ),

                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () {
                              setState(() => _timeFilter = 'Any time');
                              Navigator.pop(ctx);
                            },
                            style: OutlinedButton.styleFrom(
                              side: BorderSide(color: Colors.white.withOpacity(0.14)),
                              foregroundColor: Colors.white.withOpacity(0.9),
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                            child: const Text('Reset', style: TextStyle(fontWeight: FontWeight.w900)),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: ElevatedButton(
                            onPressed: () {
                              setState(() => _timeFilter = time);
                              Navigator.pop(ctx);
                            },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.mint.withOpacity(0.22),
                              foregroundColor: AppColors.mint,
                              elevation: 0,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                            child: const Text('Apply', style: TextStyle(fontWeight: FontWeight.w900)),
                          ),
                        ),
                      ],
                    ),
                  ],
                );
              },
            ),
          ),
        );
      },
    );
  }
}

class RecItem {
  final String title;
  final String subtitle;
  final String body;
  final double savingKwh;
  final int savingSar;

  const RecItem({
    required this.title,
    required this.subtitle,
    required this.body,
    required this.savingKwh,
    required this.savingSar,
  });
}

class _RecommendationCard extends StatelessWidget {
  final RecItem item;

  const _RecommendationCard({required this.item});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      radius: 20,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Title row
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
                  color: AppColors.mint.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.flash_on_rounded, color: AppColors.mint, size: 18),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            item.body,
            style: const TextStyle(fontSize: 12, color: AppColors.sub, height: 1.25),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              if (item.savingKwh > 0) _MiniChip(icon: Icons.bolt_rounded, text: '${item.savingKwh.toStringAsFixed(1)} kWh'),
              if (item.savingSar > 0) _MiniChip(icon: Icons.payments_rounded, text: '~ ${item.savingSar} SAR'),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniChip extends StatelessWidget {
  final IconData icon;
  final String text;

  const _MiniChip({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.mint.withOpacity(0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.mint.withOpacity(0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: AppColors.mint),
          const SizedBox(width: 6),
          Text(
            text,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: AppColors.mint),
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
