import 'observer.dart';
import 'sensor_data_reading.dart';

abstract class Device {
  final int deviceId;
  String deviceName;
  String deviceType;
  DateTime installationDate;
  final int userId;

  final List<Observer> observers = [];
  final List<SensorDataReading> sensorReadings = [];

  Device({
    required this.deviceId,
    required this.deviceName,
    required this.deviceType,
    required this.installationDate,
    required this.userId,
  });

  void collectSensorData(double kwh) {
    sensorReadings.add(
      SensorDataReading(
        timestamp: DateTime.now(),
        deviceId: deviceId,
        kwh: kwh,
      ),
    );
    notifyObservers();
  }

  String getDeviceInfo();

  void updateDeviceInfo(String newValue) {
    deviceName = newValue;
    notifyObservers();
  }

  void attach(Observer observer) {
    observers.add(observer);
  }

  void detach(Observer observer) {
    observers.remove(observer);
  }

  void notifyObservers() {
    for (final observer in observers) {
      observer.update(this);
    }
  }
}
