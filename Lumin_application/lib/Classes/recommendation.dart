import 'device.dart';
import 'device_update_handler.dart';

class Recommendation implements DeviceUpdateHandler {
  int recommendation_id;
  String recommendation_text;
  DateTime timestamp;
  int user_id;

  @override
  Device? device;

  Recommendation({
    required this.recommendation_id,
    required this.recommendation_text,
    required this.timestamp,
    required this.user_id,
  });

  String generateRecommendation(double consumptionHistory) {
    if (consumptionHistory > 0) {
      return 'Reduce consumption and shift loads to solar peak hours.';
    }
    return 'No recommendation available.';
  }

  String sendRecommendation() {
    return recommendation_text;
  }

  double getData() {
    return 0;
  }

  @override
  void update(Device device) {}
}
