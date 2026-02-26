import 'device.dart';

class ConsumptionDevice extends Device {
  double consumptionKwh;
  final double powerRating;

  ConsumptionDevice({
    required super.deviceId,
    required super.deviceName,
    required super.deviceType,
    required super.installationDate,
    required super.userId,
    required this.consumptionKwh,
    required this.powerRating,
  });

  @override
  String getDeviceInfo() {
    return 'Consumption Device: $deviceName (type: $deviceType), '
        'powerRating: $powerRating kW, consumption: $consumptionKwh kWh';
  }

  double getConsumption() {
    return consumptionKwh;
  }
}
