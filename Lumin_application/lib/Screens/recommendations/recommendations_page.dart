import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/services/api_service.dart';

class RecommendationsPage extends StatefulWidget {
  const RecommendationsPage({super.key});

  @override
  State<RecommendationsPage> createState() => _RecommendationsPageState();
}

class _RecommendationsPageState extends State<RecommendationsPage> {
  final _api = ApiService();

  int _tab = 0; // 0 = New, 1 = History
  String _timeFilter = 'Any time';

  bool _loadingNew = false;
  bool _loadingHistory = false;
  String? _error;

  List<RecItem> _newRecs = [];
  List<RecItem> _history = [];

  @override
  void initState() {
    super.initState();
    _loadNew();
    _loadHistory();
  }

  // ─── Loaders ────────────────────────────────────────────────

  Future<void> _loadNew() async {
    setState(() { _loadingNew = true; _error = null; });
    try {
      final res = await _api.generateRecommendation();
      final rec = res['recommendation'] as Map<String, dynamic>?;
      setState(() {
        _newRecs = rec != null ? [_mapToRecItem(rec, isNew: true)] : [];
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loadingNew = false);
    }
  }

  Future<void> _loadHistory() async {
    setState(() { _loadingHistory = true; _error = null; });
    try {
      final data = await _api.getAllRecommendations();
      setState(() {
        _history = data
            .cast<Map<String, dynamic>>()
            .map((r) => _mapToRecItem(r, isNew: false))
            .toList();
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loadingHistory = false);
    }
  }

  // ─── Mapping ────────────────────────────────────────────────

  RecItem _mapToRecItem(Map<String, dynamic> r, {required bool isNew}) {
    final text = r['recommendation_text'] as String? ?? '';
    final timestamp = r['timestamp'] as String?;

    String subtitle;
    if (isNew) {
      subtitle = 'Suggested • Now';
    } else if (timestamp != null) {
      final dt = DateTime.tryParse(timestamp);
      if (dt != null) {
        final diff = DateTime.now().difference(dt);
        if (diff.inMinutes < 60) {
          subtitle = '${diff.inMinutes} min ago';
        } else if (diff.inHours < 24) {
          subtitle = '${diff.inHours} hours ago';
        } else {
          subtitle = '${diff.inDays} days ago';
        }
      } else {
        subtitle = timestamp;
      }
    } else {
      subtitle = 'Past recommendation';
    }

    return RecItem(title: _extractTitle(text), subtitle: subtitle, body: text);
  }

  String _extractTitle(String text) {
    final dot = text.indexOf('.');
    if (dot > 0 && dot < 80) return text.substring(0, dot + 1);
    if (text.length > 60) return '${text.substring(0, 60)}...';
    return text;
  }

  List<RecItem> get _filteredHistory {
    if (_timeFilter == 'Any time') return _history;
    return _history.where((item) {
      if (_timeFilter == 'Today') {
        return item.subtitle.contains('min') || item.subtitle.contains('hour');
      }
      if (_timeFilter == 'This week') {
        final match = RegExp(r'(\d+) days?').firstMatch(item.subtitle);
        if (match != null) {
          final days = int.tryParse(match.group(1) ?? '') ?? 99;
          return days <= 7;
        }
        return item.subtitle.contains('min') || item.subtitle.contains('hour');
      }
      return true;
    }).toList();
  }

  List<RecItem> get _items => _tab == 0 ? _newRecs : _filteredHistory;
  bool get _loading => _tab == 0 ? _loadingNew : _loadingHistory;

  // ─── Build ───────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final items = _items;

    return GradientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        extendBody: true,
        extendBodyBehindAppBar: true,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          centerTitle: true,
          title: const Text('Recommendations',
              style: TextStyle(fontWeight: FontWeight.w900)),
          leading: IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          ),
          actions: [
            IconButton(
              tooltip: 'Refresh',
              onPressed: () { _loadNew(); _loadHistory(); },
              icon: const Icon(Icons.refresh_rounded, color: Colors.white),
            ),
          ],
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 52),

                // Error banner
                if (_error != null)
                  GlassCard(
                    radius: 14,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline_rounded,
                            color: Colors.redAccent, size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(_error!,
                              style: const TextStyle(
                                  color: Colors.redAccent, fontSize: 12)),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 16, color: Colors.white54),
                          onPressed: () => setState(() => _error = null),
                        ),
                      ],
                    ),
                  ),

                if (_error != null) const SizedBox(height: 10),

                // Counts card
                GlassCard(
                  radius: 18,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  child: Row(
                    children: [
                      Expanded(
                        child: _StatInline(
                          value: _loadingNew ? '…' : _newRecs.length.toString(),
                          label: 'New',
                        ),
                      ),
                      Container(
                          width: 1, height: 44,
                          color: Colors.white.withOpacity(0.10)),
                      Expanded(
                        child: _StatInline(
                          value: _loadingHistory ? '…' : _history.length.toString(),
                          label: 'History',
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                // Tabs + Filter
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
                    if (_tab == 1) ...[
                      const SizedBox(width: 10),
                      SizedBox(
                        height: 38,
                        child: ElevatedButton.icon(
                          onPressed: _openTimeFilterSheet,
                          icon: const Icon(Icons.tune_rounded, size: 18),
                          label: const Text('Filter',
                              style: TextStyle(fontWeight: FontWeight.w900)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.button,
                            elevation: 0,
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14)),
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),

                const SizedBox(height: 12),

                // Content
                if (_loading)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.all(32),
                      child: CircularProgressIndicator(color: AppColors.mint),
                    ),
                  )
                else if (items.isEmpty)
                  GlassCard(
                    radius: 18,
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(Icons.info_outline_rounded,
                            color: Colors.white.withOpacity(0.65)),
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
                      padding: EdgeInsets.only(
                          bottom: i == items.length - 1 ? 0 : 10),
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
    String time = _timeFilter;
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.5),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF1A1F2E),
            borderRadius: BorderRadius.circular(24),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Filter by time',
                  style: TextStyle(
                      fontWeight: FontWeight.w900,
                      fontSize: 16,
                      color: Colors.white)),
              const SizedBox(height: 14),
              ...['Any time', 'Today', 'This week', 'This month'].map((t) {
                final selected = time == t;
                return InkWell(
                  onTap: () => setLocal(() => time = t),
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: selected
                          ? AppColors.mint.withOpacity(0.14)
                          : Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color: selected
                              ? AppColors.mint.withOpacity(0.35)
                              : Colors.white12),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(t,
                              style: TextStyle(
                                  color: selected
                                      ? AppColors.mint
                                      : Colors.white70,
                                  fontWeight: FontWeight.w700)),
                        ),
                        if (selected)
                          const Icon(Icons.check_rounded,
                              color: AppColors.mint, size: 18),
                      ],
                    ),
                  ),
                );
              }).toList(),
              const SizedBox(height: 10),
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
                            borderRadius: BorderRadius.circular(14)),
                      ),
                      child: const Text('Reset',
                          style: TextStyle(fontWeight: FontWeight.w900)),
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
                            borderRadius: BorderRadius.circular(14)),
                      ),
                      child: const Text('Apply',
                          style: TextStyle(fontWeight: FontWeight.w900)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Models & Widgets ────────────────────────────────────────

class RecItem {
  final String title;
  final String subtitle;
  final String body;

  const RecItem({
    required this.title,
    required this.subtitle,
    required this.body,
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
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.title,
                        style: const TextStyle(
                            fontSize: 14, fontWeight: FontWeight.w900),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 6),
                    Text(item.subtitle,
                        style: const TextStyle(
                            fontSize: 12, color: AppColors.sub)),
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
                child: const Icon(Icons.flash_on_rounded,
                    color: AppColors.mint, size: 18),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(item.body,
              style: const TextStyle(
                  fontSize: 12, color: AppColors.sub, height: 1.25)),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String text;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChip(
      {required this.text, required this.selected, required this.onTap});

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
              color: selected
                  ? AppColors.mint.withOpacity(0.35)
                  : Colors.white12),
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
        Text(value,
            style: const TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w900,
                color: AppColors.mint)),
        const SizedBox(height: 4),
        Text(label,
            style: TextStyle(
                fontSize: 12,
                color: Colors.white.withOpacity(0.65),
                fontWeight: FontWeight.w700)),
      ],
    );
  }
}