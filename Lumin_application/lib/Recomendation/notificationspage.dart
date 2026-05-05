import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/services/api_service.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  final _api = ApiService();

  int _tab = 0; // 0=recommendations, 1=bill limit, 2=solar forecast
  bool _loading = false;
  String? _error;
  List<_NotifItem> _allNotifications = [];

  // ── Solar Forecast tab state (Sprint 2 — added by solar forecast team) ──
  // Solar notifications are fetched directly from Supabase using inFilter
  // on notification_type, bypassing the general notifications API endpoint.
  // This is intentional: solar notifications are written by DeviceMonitor
  // (backend task) and not routed through the recommendations router.
  List<_NotifItem> _solarNotifications = [];
  bool _solarLoading = false;
  // ── End solar state ──

  @override
  void initState() {
    super.initState();
    _loadNotifications();
    _loadSolarNotifications(); // Sprint 2: load solar tab on init
  }

  // ── general notifications (recommendations + bill) from API ──
  Future<void> _loadNotifications() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _api.getNotifications();
      setState(() {
        _allNotifications = data
            .cast<Map<String, dynamic>>()
            .map(_mapToNotifItem)
            .toList();
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  // ══════════════════════════════════════════════════════════
  // SOLAR FORECAST NOTIFICATIONS (Sprint 2)
  // Fetches directly from Supabase using inFilter on 3 types:
  //   - forecast_ready   : personalized forecast is available
  //   - device_warning   : device missed a daily reading
  //   - feature_disabled : device offline ≥ 15 days
  //
  // Dedup keys (#season_name_year, #warn_YYYYMMDD, #offline_since_YYYYMMDD)
  // are stripped from content before display using replaceAll(RegExp).
  // ══════════════════════════════════════════════════════════
  Future<void> _loadSolarNotifications() async {
    setState(() => _solarLoading = true);
    try {
      final client = Supabase.instance.client;
      final userId = client.auth.currentUser?.id;
      final res = await client
          .from('notification')
          .select()
          .eq('user_id', userId!)
          .inFilter('notification_type', [
            'device_warning',
            'feature_disabled',
            'forecast_ready',
          ])
          .order('timestamp', ascending: false);

      final items = (res as List).map((n) {
        final type    = n['notification_type'] as String? ?? 'device_warning';
        final content = n['content'] as String? ?? '';
        final time    = n['timestamp'] as String? ?? '';

        // Strip dedup key suffix (e.g. "#summer_2026", "#warn_2026-05-01")
        final cleanContent = content.replaceAll(RegExp(r'\s*#\w[\w-]*$'), '');

        switch (type) {
          case 'forecast_ready':
            return _NotifItem(
              title:    'Your solar forecast is ready',
              subtitle: 'Solar forecast • ${_relativeTime(time)}',
              body:     cleanContent,
              icon:     Icons.auto_graph_rounded,
              accent:   AppColors.mint,
              type:     type,
            );
          case 'feature_disabled':
            return _NotifItem(
              title:    'Solar Forecast Paused',
              subtitle: 'Solar forecast • ${_relativeTime(time)}',
              body:     cleanContent,
              icon:     Icons.power_off_rounded,
              accent:   const Color(0xFFFF5A52),
              type:     type,
            );
          default: // device_warning
            return _NotifItem(
              title:    'No Data Collected Today',
              subtitle: 'Solar forecast • ${_relativeTime(time)}',
              body:     cleanContent,
              icon:     Icons.warning_amber_rounded,
              accent:   const Color(0xFFFFC56B),
              type:     type,
            );
        }
      }).toList();

      setState(() {
        _solarNotifications = items;
        _solarLoading = false;
      });
    } catch (_) {
      setState(() => _solarLoading = false);
    }
  }

  /// Formats a UTC ISO timestamp as a human-readable relative time string.
  /// Used by solar notifications only.
  String _relativeTime(String iso) {
    try {
      final dt  = DateTime.parse(iso).toLocal();
      final now = DateTime.now();
      final d   = now.difference(dt);
      if (d.inMinutes < 1)  return 'Just now';
      if (d.inMinutes < 60) return '${d.inMinutes}m ago';
      if (d.inHours < 24)   return '${d.inHours}h ago';
      if (d.inDays == 1)    return 'Yesterday';
      return '${d.inDays} days ago';
    } catch (_) {
      return '';
    }
  }
  // ══════════════════════════════════════════════════════════
  // END SOLAR FORECAST NOTIFICATIONS
  // ══════════════════════════════════════════════════════════

  _NotifItem _mapToNotifItem(Map<String, dynamic> n) {
    final type      = n['notification_type'] as String? ?? 'general';
    final content   = n['content'] as String? ?? '';
    final timestamp = n['timestamp'] as String?;

    String timeLabel = '';
    if (timestamp != null) {
      final dt = DateTime.tryParse(timestamp);
      if (dt != null) {
        final diff = DateTime.now().difference(dt);
        if (diff.inMinutes < 60)
          timeLabel = '${diff.inMinutes} min ago';
        else if (diff.inHours < 24)
          timeLabel = '${diff.inHours} hours ago';
        else
          timeLabel = '${diff.inDays} days ago';
      }
    }

    IconData icon;
    Color accent;
    switch (type) {
      case 'recommendation' || 'bill_update':
        icon = Icons.flash_on_rounded;
        accent = AppColors.mint;
        break;
      case 'bill_warning':
        icon = Icons.warning_amber_rounded;
        accent = const Color(0xFFFFC56B);
        break;
      default:
        icon = Icons.notifications_rounded;
        accent = AppColors.mint;
    }

    return _NotifItem(
      title:    _extractTitle(content),
      subtitle: timeLabel.isNotEmpty ? '$type • $timeLabel' : type,
      body:     content,
      icon:     icon,
      accent:   accent,
      type:     type,
    );
  }

  String _extractTitle(String text) {
    final dot = text.indexOf('.');
    if (dot > 0 && dot < 80) return text.substring(0, dot + 1);
    if (text.length > 60) return '${text.substring(0, 60)}...';
    return text;
  }

  List<_NotifItem> get _items {
    if (_tab == 1)
      return _allNotifications
          .where((n) => n.type == 'bill_warning' || n.type == 'bill_update')
          .toList();
    if (_tab == 2) return _solarNotifications; // Sprint 2: solar tab
    return _allNotifications.where((n) => n.type == 'recommendation').toList();
  }

  // Sprint 2: solar tab uses its own loading state
  bool get _isLoading => _tab == 2 ? _solarLoading : _loading;

  String get _emptyText {
    if (_tab == 1) return 'No bill limit notifications right now.';
    if (_tab == 2) return 'No solar forecast notifications right now.';
    return 'No recommendation notifications right now.';
  }

  String get _sectionTitle {
    if (_tab == 1) return 'Bill Limit';
    if (_tab == 2) return 'Solar Forecast';
    return 'Recommendations';
  }

  void _refresh() {
    if (_tab == 2) {
      _loadSolarNotifications(); // Sprint 2: manual refresh for solar tab
    } else {
      _loadNotifications();
    }
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
          icon: const Icon(
            Icons.arrow_back_ios_new_rounded,
            color: Colors.white,
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh_rounded, color: Colors.white),
          ),
        ],
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_error != null) ...[
              GlassCard(
                radius: 14,
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 10,
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.error_outline_rounded,
                      color: Colors.redAccent,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _error!,
                        style: const TextStyle(
                          color: Colors.redAccent,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(
                        Icons.close,
                        size: 16,
                        color: Colors.white54,
                      ),
                      onPressed: () => setState(() => _error = null),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 10),
            ],

            // Filter chips
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
                  // Sprint 2: Solar Forecast tab
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

            if (_isLoading)
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
                    Icon(
                      Icons.info_outline_rounded,
                      color: Colors.white.withOpacity(0.65),
                    ),
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
              ...List.generate(
                items.length,
                (i) => Padding(
                  padding: EdgeInsets.only(
                    bottom: i == items.length - 1 ? 0 : 10,
                  ),
                  child: _NotifCard(item: items[i]),
                ),
              ),

            const SizedBox(height: 18),
          ],
        ),
      ),
    );
  }
}

// ══════════════════════════════════════════════════════════
//  DATA MODEL
// ══════════════════════════════════════════════════════════

class _NotifItem {
  final String title, subtitle, body, type;
  final IconData icon;
  final Color accent;

  const _NotifItem({
    required this.title,
    required this.subtitle,
    required this.body,
    required this.icon,
    required this.accent,
    required this.type,
  });
}

// ══════════════════════════════════════════════════════════
//  NOTIFICATION CARD
// ══════════════════════════════════════════════════════════

class _NotifCard extends StatelessWidget {
  final _NotifItem item;
  const _NotifCard({required this.item});

  @override
  Widget build(BuildContext context) => GlassCard(
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
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w900,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    item.subtitle,
                    style: const TextStyle(fontSize: 12, color: AppColors.sub),
                  ),
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
        if (item.body.isNotEmpty) ...[
          const SizedBox(height: 10),
          Text(
            item.body,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.sub,
              height: 1.25,
            ),
          ),
        ],
      ],
    ),
  );
}

// ══════════════════════════════════════════════════════════
//  FILTER CHIP
// ══════════════════════════════════════════════════════════

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
  Widget build(BuildContext context) => InkWell(
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