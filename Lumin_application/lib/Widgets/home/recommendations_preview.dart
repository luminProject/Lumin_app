import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../services/api_service.dart';
import 'glass_card.dart';

class RecommendationsPreview extends StatefulWidget {
  final VoidCallback? onSeeAll;

  const RecommendationsPreview({
    super.key,
    this.onSeeAll,
  });

  @override
  State<RecommendationsPreview> createState() => _RecommendationsPreviewState();
}

class _RecommendationsPreviewState extends State<RecommendationsPreview> {
  final _api = ApiService();

  bool _loading = true;
  String? _error;
  _RecItem? _item;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) setState(() { _loading = true; _error = null; });
    try {
      final res = await _api.getLatestRecommendation();

      if (res != null) {
        // Check if the recommendation is from today
        final timestamp = res['timestamp'] as String?;
        final isToday = _isToday(timestamp);

        if (isToday) {
          if (mounted) setState(() => _item = _map(res));
        } else {
          // Latest recommendation exists but it's from a previous day
          if (mounted) setState(() => _item = null);
        }
      } else {
        // No recommendations at all
        if (mounted) setState(() => _item = null);
      }
    } catch (e) {
      if (mounted) setState(() => _error = _friendlyError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _friendlyError(Object e) {
    final msg = e.toString().toLowerCase();
    if (msg.contains('socket') ||
        msg.contains('connection') ||
        msg.contains('network') ||
        msg.contains('timeout')) {
      return 'No internet connection.';
    }
    if (msg.contains('500') || msg.contains('server')) {
      return 'Server unavailable. Try again soon.';
    }
    return 'Could not load recommendation.';
  }

  bool _isToday(String? timestamp) {
    if (timestamp == null) return false;
    final dt = DateTime.tryParse(timestamp)?.toLocal();
    if (dt == null) return false;
    final now = DateTime.now();
    return dt.year == now.year && dt.month == now.month && dt.day == now.day;
  }

  _RecItem _map(Map<String, dynamic> r) {
    final text = r['recommendation_text'] as String? ?? '';
    // First sentence → title, rest → reason
    final dot = text.indexOf('.');
    final title = (dot > 0 && dot < 80) ? text.substring(0, dot + 1) : text;
    final reason = (dot > 0 && dot < text.length - 1)
        ? text.substring(dot + 1).trim()
        : '';
    return _RecItem(title: title, reason: reason);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Row(
          children: [
            const Text(
              'Smart Recommendations',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const Spacer(),
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

        // Content
        if (_loading)
          GlassCard(
            radius: 20,
            padding: const EdgeInsets.symmetric(vertical: 28),
            child: const Center(
              child: SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  color: AppColors.mint,
                  strokeWidth: 2.5,
                ),
              ),
            ),
          )
        else if (_error != null)
          GlassCard(
            radius: 20,
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                const Icon(Icons.cloud_off_rounded,
                    color: Colors.redAccent, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    _error!,
                    style: TextStyle(
                        color: Colors.white.withOpacity(0.85),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600),
                  ),
                ),
                TextButton(
                  onPressed: _load,
                  style: TextButton.styleFrom(
                    foregroundColor: AppColors.mint,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: const Text('Retry',
                      style: TextStyle(
                          fontWeight: FontWeight.w800, fontSize: 12)),
                ),
              ],
            ),
          )
        else if (_item == null)
          GlassCard(
            radius: 20,
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Icon(Icons.lightbulb_outline_rounded,
                    color: AppColors.mint.withOpacity(0.65), size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'No recommendation yet today',
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.85),
                            fontSize: 13,
                            fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Check back later for your next tip.',
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 11.5),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          )
        else
          _RecommendationCard(item: _item!),
      ],
    );
  }
}

// ─── Models ──────────────────────────────────────────────────

class _RecItem {
  final String title;
  final String reason;

  const _RecItem({required this.title, required this.reason});
}

// ─── Widgets ─────────────────────────────────────────────────

class _RecommendationCard extends StatelessWidget {
  final _RecItem item;
  const _RecommendationCard({required this.item});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      radius: 20,
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
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
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  item.title,
                  style: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w800),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          if (item.reason.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              item.reason,
              style: const TextStyle(
                  fontSize: 12, color: AppColors.sub, height: 1.2),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
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
            style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: AppColors.mint),
          ),
        ],
      ),
    );
  }
}