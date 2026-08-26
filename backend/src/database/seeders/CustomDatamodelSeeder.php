<?php

namespace Database\Seeders;

use App\Models\CustomDatamodel;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;


class CustomDatamodelSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $this->createCustomDatamodels();
    }

    private function createCustomDatamodels()
    {
        $commands = [
            [
                'device_type_id' => 3,
                'command' => 'reboot',
                'name' => 'Reboot',
                'description' => 'Reboot the device',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'bool',
                'units' => 'dimensionless',
            ],
            [
                'device_type_id' => 3,
                'command' => 'numLoopsToSend',
                'name' => 'Number of Loops to Send',
                'description' => 'Number of loops to send',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'uint8_t',
                'units' => 'dimensionless',
            ],
            [
                'device_type_id' => 3,
                'command' => 'loopTime',
                'name' => 'Loop Time',
                'description' => 'Loop time',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'uint8_t',
                'units' => 'dimensionless',
            ],
            [
                'device_type_id' => 3,
                'command' => 'enableGps',
                'name' => 'Enable GPS',
                'description' => 'Enable GPS',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'bool',
                'units' => 'dimensionless',
            ],
            [
                'device_type_id' => 3,
                'command' => 'enableSocketA',
                'name' => 'Enable Socket A',
                'description' => 'Enable Socket A',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'bool',
                'units' => 'dimensionless',
            ],
            [
                'device_type_id' => 3,
                'command' => 'enableSocketB',
                'name' => 'Enable Socket B',
                'description' => 'Enable Socket B',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'bool',
                'units' => 'dimensionless',
            ],
            [
                'device_type_id' => 3,
                'command' => 'enableSocketC',
                'name' => 'Enable Socket C',
                'description' => 'Enable Socket C',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'bool',
                'units' => 'dimensionless',
            ],
            [
                'device_type_id' => 3,
                'command' => 'enableSocketD',
                'name' => 'Enable Socket D',
                'description' => 'Enable Socket D',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'bool',
                'units' => 'dimensionless',
            ],
            [
                'device_type_id' => 3,
                'command' => 'ota',
                'name' => 'OTA',
                'description' => 'OTA',
                'send_type' => 'Uplink',
                'operations' => 'r',
                'data_types' => 'bool',
                'units' => 'dimensionless',
            ],
        ];

        CustomDatamodel::insert($commands);

    }
}
