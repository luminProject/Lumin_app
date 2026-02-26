import 'device.dart';
import 'device_update_handler.dart';

class EnergyCalculation implements DeviceUpdateHandler {
  int energy_id;
  DateTime date;
  double total_consumption;
  double total_production;
  double cost_savings;
  double carbon_reduction;
  int user_id;

  static const List<double> TARIFF = [0.18, 0.30];

  @override
  Device? device;

  EnergyCalculation({
    required this.energy_id,
    required this.date,
    required this.total_consumption,
    required this.total_production,
    required this.cost_savings,
    required this.carbon_reduction,
    required this.user_id,
  });

  void calculateEnergy() {
    final solarUsed = total_production < total_consumption
        ? total_production
        : total_consumption;
    cost_savings = calculateCostSavings(solarUsed);
    carbon_reduction = calculateCarbonReduction(solarUsed);
  }

  int getEnergyId() {
    return energy_id;
  }

  double calculateCostSavings([double? value]) {
    final v = value ?? 0;
    return v * TARIFF[0];
  }

  double calculateCarbonReduction([double? solarUsed]) {
    final v = solarUsed ?? 0;
    const factor = 0.7;
    return v * factor;
  }

  void viewSummary(Duration interval) {
    calculateEnergy();
  }

  void displayRealTimeEnergy() {
    calculateEnergy();
  }

  @override
  void update(Device device) {}
}
