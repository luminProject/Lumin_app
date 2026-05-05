import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

/// ApiService handles all HTTP requests to the FastAPI backend.
///
/// Important:
/// - Backend baseUrl changes depending on platform:
///   - Web:        http://127.0.0.1:8000
///   - Android emu http://10.0.2.2:8000
///
/// Auth:
/// - Profile endpoints are protected.
/// - We send Supabase session access token in:
///     Authorization: Bearer <token>
class ApiService {
  /// Base URL for backend depending on current platform.
  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000';
    if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    return 'http://127.0.0.1:8000';
  }

  // ===== Helpers =====

  /// Returns current Supabase user id.
  /// Throws if user is not logged in.
  String get _userId {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) throw Exception('User not logged in');
    return user.id;
  }

  /// Returns current Supabase access token.
  /// Throws if there is no active session.
  String get _accessToken {
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    if (token == null) throw Exception('No access token');
    return token;
  }

  /// Returns headers including authorization.
  ///
  /// If [json] is true, it also sets Content-Type to application/json.
  Map<String, String> authHeaders({bool json = false}) {
    final headers = <String, String>{
      'Authorization': 'Bearer $_accessToken',
      'accept': 'application/json',
    };
    if (json) headers['Content-Type'] = 'application/json';
    return headers;
  }

  // ===== Devices =====

  /// GET /devices/{userId}
  Future<List<dynamic>> getDevices() async {
    final response = await http.get(Uri.parse('$baseUrl/devices/$_userId'));
    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'] ?? [];
    } else {
      throw Exception('Failed to load devices');
    }
  }

  /// POST /devices/{userId}
  Future<void> addDevice({
    required String deviceName,
    required String deviceType,
    String? panelCapacity,
    bool isShiftable = false,
  }) async {
    final body = {
      "name": deviceName,
      "device_type": deviceType,
      "panel_capacity": panelCapacity,
      "is_shiftable": deviceType == 'consumption' ? isShiftable : false,
    };
    final response = await http.post(
      Uri.parse('$baseUrl/devices/$_userId'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to add device');
    }
  }

  /// DELETE /devices/{deviceId}
  Future<void> deleteDevice(int deviceId) async {
    final response = await http.delete(Uri.parse('$baseUrl/devices/$deviceId'));
    if (response.statusCode != 200) {
      throw Exception('Failed to delete device');
    }
  }

  /// PATCH /devices/{deviceId}
  /// Updates editable device settings only.
  /// Never sends created_at.
  Future<void> updateDeviceSettings({
    required int deviceId,
    required String deviceName,
    required String deviceType,
    String? room,
    String? panelCapacity,
  }) async {
    final body = {
      'name': deviceName,
      'device_type': deviceType,
      'room': deviceType == 'production' ? null : room,
      'panel_capacity': deviceType == 'production' ? panelCapacity : null,
    };

    final response = await http.patch(
      Uri.parse('$baseUrl/devices/$deviceId'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to update device settings');
    }
  }

  /// GET /sensor-readings/{deviceId}
  Future<List<dynamic>> getDeviceReadings(int deviceId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/sensor-readings/$deviceId'),
    );

    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'] ?? [];
    } else {
      throw Exception('Failed to load device readings');
    }
  }

  /// GET /sensor-readings/latest/{deviceId}
  Future<Map<String, dynamic>?> getLatestReading(int deviceId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/sensor-readings/latest/$deviceId'),
    );

    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'] as Map<String, dynamic>?;
    } else {
      throw Exception('Failed to load latest reading');
    }
  }

  // ===== Bill =====

  /// GET /bill/{userId}
  Future<Map<String, dynamic>> getBill() async {
    final url = '$baseUrl/bill/$_userId';

    final response = await http.get(Uri.parse(url), headers: authHeaders());

    debugPrint('GET BILL -> $url');
    debugPrint('GET BILL <- status=${response.statusCode}');
    debugPrint('GET BILL <- body=${response.body}');

    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'];
    } else {
      throw Exception('Failed to load bill prediction: ${response.body}');
    }
  }

  /// POST /bill/{userId}
  Future<Map<String, dynamic>> setBillLimit(double billLimit) async {
    final url = '$baseUrl/bill/$_userId';

    final response = await http.post(
      Uri.parse(url),
      headers: authHeaders(json: true),
      body: json.encode({'limit_amount': billLimit}),
    );

    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'];
    } else if (response.statusCode == 401 || response.statusCode == 403) {
      throw Exception('Your session has expired. Please sign in again.');
    } else {
      String message =
          'Unable to save your bill limit right now. Please try again.';

      try {
        final errorBody = json.decode(response.body);
        if (errorBody is Map && errorBody['detail'] != null) {
          message = errorBody['detail'].toString();
        }
      } catch (_) {}

      throw Exception(message);
    }
  }

  // ===== Energy =====

  /// GET /energy/{userId}
  Future<Map<String, dynamic>> getEnergyStats() async {
    final response = await http.get(Uri.parse('$baseUrl/energy/$_userId'));
    if (response.statusCode == 200) {
      return json.decode(response.body)['data'];
    } else {
      throw Exception('Failed to load energy stats');
    }
  }

  // ===== Statistics Chart (Sprint 2) =====

  /// GET /stats/{userId}?range=week|month|year&anchor=...
  ///
  /// anchor format:
  ///   week  → YYYY-MM-DD (any day within the target week)
  ///   month → YYYY-MM
  ///   year  → YYYY
  Future<Map<String, dynamic>> getStats({
    required String range,
    required String anchor,
  }) async {
    final response = await http.get(
      Uri.parse('$baseUrl/stats/$_userId?range=$range&anchor=$anchor'),
      headers: authHeaders(),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body)['data'];
    } else {
      throw Exception('Failed to load stats: ${response.statusCode}');
    }
  }

  // ===== Solar Forecast (Sprint 2 — Solar Forecast feature) =====

  /// GET /solar-forecast/{userId}
  /// Returns the current forecast state for the user's solar system.
  /// State machine cases: no_panels | collecting | collecting_extended |
  ///                      forecast_available | feature_disabled
  Future<Map<String, dynamic>> getSolarForecast() async {
    final response = await http.get(
      Uri.parse('$baseUrl/solar-forecast/$_userId'),
      headers: authHeaders(),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body)['data'];
    } else {
      throw Exception('Failed to load solar forecast: ${response.statusCode}');
    }
  }

  /// POST /solar-forecast/{userId}/check-device
  /// Called from feature_disabled screen to check if device reconnected.
  /// Returns: { reconnected: bool }
  Future<Map<String, dynamic>> checkSolarDevice() async {
    final response = await http.post(
      Uri.parse('$baseUrl/solar-forecast/$_userId/check-device'),
      headers: authHeaders(),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Device check failed: ${response.statusCode}');
  }

  // ===== Recommendations =====

  /// POST /recommendations/generate/{userId}
  ///
  /// Generates a new recommendation based on solar + device data,
  /// saves it to DB, and also creates a notification automatically.
  Future<Map<String, dynamic>> generateRecommendation() async {
    final response = await http.post(
      Uri.parse('$baseUrl/recommendations/generate/$_userId'),
      headers: authHeaders(),
    );
    debugPrint('GENERATE REC <- status=${response.statusCode}');
    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to generate recommendation: ${response.body}');
    }
  }

  /// GET /recommendations/latest/{userId}
  ///
  /// Returns the most recently generated recommendation.
  Future<Map<String, dynamic>?> getLatestRecommendation() async {
    final response = await http.get(
      Uri.parse('$baseUrl/recommendations/latest/$_userId'),
      headers: authHeaders(),
    );
    debugPrint('GET LATEST REC <- status=${response.statusCode}');
    if (response.statusCode == 200) {
      final body = json.decode(response.body) as Map<String, dynamic>;
      return body['data'] as Map<String, dynamic>?;
    } else {
      throw Exception('Failed to load latest recommendation: ${response.body}');
    }
  }

  /// GET /recommendations/all/{userId}
  ///
  /// Returns all past recommendations ordered newest first.
  Future<List<dynamic>> getAllRecommendations() async {
    final response = await http.get(
      Uri.parse('$baseUrl/recommendations/all/$_userId'),
      headers: authHeaders(),
    );
    debugPrint('GET ALL RECS <- status=${response.statusCode}');
    if (response.statusCode == 200) {
      final body = json.decode(response.body) as Map<String, dynamic>;
      return body['data'] ?? [];
    } else {
      throw Exception('Failed to load recommendations: ${response.body}');
    }
  }

  // ===== Notifications =====

  /// GET /recommendations/notifications/{userId}
  ///
  /// Returns all notifications for the user ordered newest first.
  Future<List<dynamic>> getNotifications() async {
    final response = await http.get(
      Uri.parse('$baseUrl/recommendations/notifications/$_userId'),
      headers: authHeaders(),
    );
    debugPrint('GET NOTIFICATIONS <- status=${response.statusCode}');
    if (response.statusCode == 200) {
      final body = json.decode(response.body) as Map<String, dynamic>;
      return body['data'] ?? [];
    } else {
      throw Exception('Failed to load notifications: ${response.body}');
    }
  }

  /// GET /recommendations/notifications/latest/{userId}
  ///
  /// Returns the most recent notification.
  Future<Map<String, dynamic>?> getLatestNotification() async {
    final response = await http.get(
      Uri.parse('$baseUrl/recommendations/notifications/latest/$_userId'),
      headers: authHeaders(),
    );
    debugPrint('GET LATEST NOTIFICATION <- status=${response.statusCode}');
    if (response.statusCode == 200) {
      final body = json.decode(response.body) as Map<String, dynamic>;
      return body['data'] as Map<String, dynamic>?;
    } else {
      throw Exception('Failed to load latest notification: ${response.body}');
    }
  }

  // ===== Real-Time Monitoring =====

  /// GET /realtime/{userId}
  /// Returns live device readings for the Home page.
  /// Called every 5 seconds by a Timer in HomePage.
  Future<Map<String, dynamic>> getRealtimeData() async {
    final response = await http.get(
      Uri.parse('$baseUrl/realtime/$_userId'),
    );
    if (response.statusCode == 200) {
      final body = json.decode(response.body) as Map<String, dynamic>;
      return body['data'] as Map<String, dynamic>? ?? {};
    } else {
      throw Exception('Failed to load realtime data: ${response.statusCode}');
    }
  }

  // ===== Profile =====

  /// GET /profiles/{userId}
  Future<Map<String, dynamic>> getProfile(String userId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/profiles/$userId'),
      headers: authHeaders(),
    );
    if (res.statusCode >= 400) {
      throw Exception('GET ${res.statusCode}: ${res.body}');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// PATCH /profiles/{userId}
  Future<void> updateProfile(
    String userId,
    Map<String, dynamic> payload,
  ) async {
    final res = await http.patch(
      Uri.parse('$baseUrl/profiles/$userId'),
      headers: authHeaders(json: true),
      body: jsonEncode(payload),
    );
    if (res.statusCode >= 400) {
      throw Exception('PATCH ${res.statusCode}: ${res.body}');
    }
  }

  /// Convenience wrapper to update only the avatar_url.
  Future<void> updateAvatarUrl(String userId, String avatarUrl) async {
    await updateProfile(userId, {'avatar_url': avatarUrl});
  }
}