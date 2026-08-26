<?php

namespace Database\Seeders;

use App\Models\DeviceType;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Log;


class DeviceTypesSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $this->createDeviceTypes();
    }

    private function createDeviceTypes()
    {
        $deviceTypes = [
            [
                'id' => 1,
                'name' => 'Smart Parking V2',
                "brand" => "Libelium",
                'category' => 'Smart Parking',
                'code' => 'parking',
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'ParkingSpot'
                ])
            ],
            [
                'id' => 2,
                'name' => 'Air Quality Station',
                "brand" => "Libelium",
                'category' => 'Air Quality Station',
                'code' => 'aqs',
                'fiware_properties' => null
            ],
            [
                "id" => 3,
                "name" => "ONE",
                "brand" => "Libelium",
                "category" => "One",
                "code" => "one",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'LibeliumOne'
                ])
            ],
            [
                "id" => 4,
                "name" => "Smart Spot",
                "brand" => "Libelium",
                "category" => "Smart Spot",
                "code" => "smsp",
                'fiware_properties' => json_encode([
                    "protocol" => "MQTT",
                    "default_datamodel" => "Device",
                    "extra_datamodels" => [
                        ["value" => "aqo", "datamodel" => "AirQualityObserved"],
                        ["value" => "nlo", "datamodel" => "NoiseLevelObserved"],
                        ["value" => "cfe", "datamodel" => "CrowdFlowEvent"],
                        ["value" => "cfo", "datamodel" => "CrowdFlowObserved"],
                        ["value" => "wto", "datamodel" => "WeatherObserved"],
                        ["value" => "dev", "datamodel" => "Device"],
                        ["value" => "dho", "datamodel" => "DeviceHealthObserved"],
                        ["value" => "irr", "datamodel" => "Irrigation"]
                    ]
                ])
            ],
            [
                "id" => 5,
                "name" => "Smart Parking V3 NB",
                "brand" => "Libelium",
                "category" => "Smart Parking",
                "code" => "parking_v3_nb",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'ParkingSpot'
                ])
            ],
            [
                "id" => 6,
                "name" => "Smart Parking V3 Lorawan",
                "brand" => "Libelium",
                "category" => "Smart Parking",
                "code" => "parking_v3_lorawan",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'ParkingSpot'
                ])
            ],
            [
                "id" => 7,
                "name" => "ONE",
                "brand" => "Libelium",
                "category" => "One",
                "code" => "one_fiware",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'Device'
                ])
            ],
            [
                "id" => 8,
                "name" => "Smart Spot Fiware",
                "brand" => "Libelium",
                "category" => "Smart Spot",
                "code" => "smsp_fiware",
                'fiware_properties' => json_encode([
                    "protocol" => "HTTP",
                    "default_datamodel" => "Device",
                    "extra_datamodels" => [
                        ["value" => "aqo", "datamodel" => "AirQualityObserved"],
                        ["value" => "nlo", "datamodel" => "NoiseLevelObserved"],
                        ["value" => "cfe", "datamodel" => "CrowdFlowEvent"],
                        ["value" => "cfo", "datamodel" => "CrowdFlowObserved"],
                        ["value" => "wto", "datamodel" => "WeatherObserved"],
                        ["value" => "dev", "datamodel" => "Device"],
                        ["value" => "dho", "datamodel" => "DeviceHealthObserved"],
                        ["value" => "irr", "datamodel" => "Irrigation"]
                    ]
                ])
            ],
            [
                "id" => 9,
                "name" => "Parking BLE",
                "brand" => "Libelium",
                "category" => "Beacon",
                "code" => "parking_ble",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'Device'
                ])
            ],
            [
                "id" => 10,
                "name" => "CORE",
                "brand" => "Libelium",
                "category" => "Core",
                "code" => "core",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'Device'
                ])
            ],
            [
                "id" => 100,
                "name" => "Magnetic Sensor",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "ws301",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'WeatherObserved'
                ])
            ],
            [
                "id" => 101,
                "name" => "Indoor Ambience Monitor",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "am103",
                'fiware_properties' => null
            ],
            [
                "id" => 102,
                "name" => "PIR & Light Sensor",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "ws202",
                'fiware_properties' => null
            ],
            [
                "id" => 103,
                "name" => "Sound Level Sensor",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "ws302",
                'fiware_properties' => null
            ],
            [
                "id" => 104,
                "name" => "Outdoor Environment Monitoring",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "em500_co2",
                'fiware_properties' => null
            ],
            [
                "id" => 105,
                "name" => "Residential Gas Detector",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "gs101",
                'fiware_properties' => null
            ],
            [
                "id" => 106,
                "name" => "IoT Magnet Switch Sensor",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "em300_mcs",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'WeatherObserved'
                ])
            ],
            [
                "id" => 107,
                "name" => "IoT Spot Leak Sensor",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "em300_sld",
                'fiware_properties' => null
            ],
            [
                "id" => 108,
                "name" => "IoT Temperature Humidity Sensor",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "em300_th",
                'fiware_properties' => null
            ],
            [
                "id" => 109,
                "name" => "Third Party Device",
                "code" => "third_party_device",
                "brand" => "ThirdParty",
                "category" => "ThirdParty",
                'fiware_properties' => json_encode([
                    'default_datamodel' => 'Device',
                    "extra_datamodels" => [
                        ["value" => "alert", "datamodel" => "Alert"],
                        ["value" => "stix", "datamodel" => "STIX"],
                        ["value" => "vehicle", "datamodel" => "Vehicle"],
                        ["value" => "vehicle", "datamodel" => "VehicleDetector"],
                        ["value" => "traffic_flow", "datamodel" => "TrafficFlowObserved"],
                        ["value" => "traffic_camera", "datamodel" => "TrafficCamera"],
                        ["value" => "camera", "datamodel" => "Camera"],
                        ["value" => "device", "datamodel" => "Device"],
                        ["value" => "electricity_consumption_cost", "datamodel" => "ElectricityConsumptionCost"],
                        ["value" => "water_consumption_cost", "datamodel" => "WaterConsumptionCost"],
                        ["value" => "gas_consumption_cost", "datamodel" => "GasConsumptionCost"],
                        ["value" => "consumption_point", "datamodel" => "ConsumptionPoint"],
                    ]
                ])
            ],
            [
                "id" => 110,
                "name" => "CESVA TA150",
                "code" => "cesva_ta150",
                "brand" => "CESVA",
                "category" => "CESVA Noise",
                'fiware_properties' => json_encode([
                    'protocol' => 'HTTP',
                    'default_datamodel' => 'NoiseLevelObserved'
                ])
            ],
            [
                "id" => 111,
                "name" => "Decentlab DL-PR36",
                "brand" => "Decentlab",
                "category" => "LoRaWAN",
                "code" => "dl_pr36",
                'fiware_properties' => null
            ],
            [
                "id" => 112,
                "name" => "Residual Chlorine Sensor",
                "brand" => "Dragino",
                "category" => "LoRaWAN",
                "code" => "dl_wqs_cl",
                'fiware_properties' => null
            ],
            [
                "id" => 113,
                "name" => "CR350 Fuel moisture and temp. station",
                "brand" => "ODINS",
                "category" => "LoRaWAN",
                "code" => "fm_cr350",
                'fiware_properties' => null
            ],
            [
                "id" => 114,
                "name" => "DL-PM Air quality",
                "brand" => "Decentlab",
                "category" => "LoRaWAN",
                "code" => "dl_pm",
                'fiware_properties' => null
            ],
            [
                "id" => 115,
                "name" => "DL-TRS12 Elect conductivity",
                "brand" => "Decentlab",
                "category" => "LoRaWAN",
                "code" => "dl_trs12",
                'fiware_properties' => null
            ],
            [
                "id" => 116,
                "name" => "DL-ATM41G2 Weather Station",
                "brand" => "Decentlab",
                "category" => "LoRaWAN",
                "code" => "dl_atm41g2",
                'fiware_properties' => null
            ],
            [
                "id" => 117,
                "name" => "AM319 HCHO Indoor Ambience",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "am319",
                'fiware_properties' => null
            ],
            [
                "id" => 118,
                "name" => "AT101 Outdoor Asset Tracker",
                "brand" => "Milesight",
                "category" => "LoRaWAN",
                "code" => "at101",
                'fiware_properties' => null
            ],
            [
                "id" => 119,
                "name" => "Digitanimal ECO",
                "brand" => "Digitanimal",
                "category" => "LoRaWAN",
                "code" => "da_eco",
                'fiware_properties' => null
            ]
        ];

        foreach ($deviceTypes as $deviceType) {
            if (isset($deviceType['fiware_properties']) && is_string($deviceType['fiware_properties'])) {
                $deviceType['fiware_properties'] = json_decode($deviceType['fiware_properties'], true);
            }

            $dt = DeviceType::updateOrCreate(
                ['code' => $deviceType['code']],
                $deviceType
            );

            if ($dt->wasRecentlyCreated) {
                Log::info('CREATED new device type', ['code' => $dt->code, 'id' => $dt->id]);
            } else {
                Log::info('FOUND existing device type', ['code' => $dt->code, 'id' => $dt->id]);
            }
        }
    }
}
