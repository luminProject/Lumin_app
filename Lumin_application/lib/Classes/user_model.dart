/// UserModel represents the user profile data that the app edits/reads.
///
/// This model is built to match the JSON keys returned by the backend endpoint:
///   GET /profiles/{userId}
///
/// Expected JSON keys (backend):
/// - username (String)
/// - phone_number (String)
/// - avatar_url (String | null)
/// - energy_source (String | null)  -> defaults to 'Grid only'
/// - latitude (num | null)
/// - longitude (num | null)
///
/// Notes:
/// - `avatarUrl` is NOT included in `toUpdateJson()` on purpose.
///   Avatar is updated through a separate flow after uploading to Supabase Storage.
class UserModel {
  /// User full name displayed in the UI.
  final String username;

  /// Full phone number including country code (example: +9665xxxxxxx).
  final String phoneNumber;

  /// Public URL for the avatar image (Supabase Storage public URL).
  /// Can be null/empty -> UI should show no image with no error.
  final String? avatarUrl;

  /// Selected energy source in UI.
  /// Example values:
  /// - "Grid only"
  /// - "Grid + Solar"
  final String energySource;

  /// Home latitude (optional).
  final double? latitude;

  /// Home longitude (optional).
  final double? longitude;

  const UserModel({
    required this.username,
    required this.phoneNumber,
    required this.energySource,
    this.avatarUrl,
    this.latitude,
    this.longitude,
  });

  /// Builds a UserModel from backend JSON.
  ///
  /// Handles defaults and safe conversions:
  /// - energy_source default => 'Grid only'
  /// - avatar_url empty => null
  /// - latitude/longitude numeric => double
  factory UserModel.fromJson(Map<String, dynamic> json) {
    final avatar = (json['avatar_url'] ?? '').toString().trim();

    final lat = json['latitude'];
    final lon = json['longitude'];

    String energy = (json['energy_source'] ?? 'Grid only').toString().trim();
    if (energy.isEmpty) energy = 'Grid only';

    return UserModel(
      username: (json['username'] ?? '').toString().trim(),
      phoneNumber: (json['phone_number'] ?? '').toString().trim(),
      avatarUrl: avatar.isEmpty ? null : avatar,
      energySource: energy,
      latitude: (lat is num) ? lat.toDouble() : null,
      longitude: (lon is num) ? lon.toDouble() : null,
    );
  }

  /// Builds the payload used to update the profile through:
  ///   PATCH /profiles/{userId}
  ///
  /// Avatar is intentionally excluded here, because it is updated separately
  /// after uploading the image to Supabase Storage.
  Map<String, dynamic> toUpdateJson() {
    return {
      'username': username.trim(),
      'phone_number': phoneNumber.trim(),
      'energy_source': energySource.trim(),
      'latitude': latitude,
      'longitude': longitude,
    };
  }
}