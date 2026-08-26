<?php

/**
 *This command will update the custom datamodels table with the data from the CSV files in the storage folder.
 */

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Models\CustomDatamodel;
use App\Models\CustomDatamodelMapping;
use App\Models\Probe;
use App\Models\ProbeType;
use League\Csv\Reader;

class updateProbesCustomDatamodels extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'app:update-probes-custom-datamodels';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Update custom datamodels table for probe measurements';

    /**
     * Execute the console command.
     */
    public function handle()
    {
        $this->info('Reading CSV file');
        $reader = Reader::createFromPath(storage_path('app/CSV/probes/one_sensor_datamodel.csv'), 'r');
        $reader->setHeaderOffset(0);

        $this->updateProbeTypes($reader);

        $records = $reader->getRecords();
        $this->updateCustomDatamodels($records);
    }

    private function updateProbeTypes(Reader $reader)
    {
        $probeTypes = iterator_to_array($reader->fetchColumnByName('Sensor name'), false);
        $probeTypes = array_unique(array_filter($probeTypes));

        # Generic type for null probe types
        $probeTypes[] = 'GENERIC_ONE_PROBE';

        // save the probe types to the probe_types table
        $this->info('Updating probe types');
        foreach ($probeTypes as $probeType) {
            ProbeType::updateOrCreate(
                ['name' => $probeType],
                [
                    'name' => $probeType,
                    'code' => strtolower($probeType)
                ]
            );
        }
        $this->info('Probe types updated');
    }

    private function updateCustomDatamodels($records)
    {
        $this->info('Updating custom datamodels table');
        $genericProbeType = ProbeType::where('name', 'GENERIC_ONE_PROBE')->first();

        foreach ($records as $record) {
            $probeType = ProbeType::where('name', $record['Sensor name'])->first();

            if (!$probeType) {
                $probeType = $genericProbeType;
            }

            $probeTypeId = $probeType->id;
            $record['Min'] = $record['Min'] == 'N/A' ? null : (int)$record['Min'];
            $record['Max'] = $record['Max'] == 'N/A' ? null : (int)$record['Max'];
            $record['Internal'] = $record['Internal'] == 'Yes' ? true : false;
            $record['Template'] = $record['Template'] == 'Yes' ? true : false;

            $this->info('Updating ' . $record['Command']);
            $customDatamodel = CustomDatamodel::updateOrCreate(
                [
                    'resource_type' => ProbeType::class,
                    'resource_id' => $probeTypeId,
                    'command' => $record['Command']
                ],
                [
                    'resource_type' => ProbeType::class,
                    'resource_id' => $probeTypeId,
                    'command' => $record['Command'],
                    'name' => $record['Name'],
                    'description' => $record['Description'],
                    'operations' => $record['Operations'],
                    'data_types' => $record['Data type'],
                    'units' => $record['Units'],
                    'tab' => $record['Tab'] ?? null,
                    'datamodel' => $record['Datamodel'] ?? null,
                    'min' => $record['Min'],
                    'max' => $record['Max'],
                    'internal' => $record['Internal'],
                    'firmware_version' => $record['Firmware version'] ?? null,
                    'template' => $record['Template']
                ]
            );
            if (!empty($record['Mapping']) && !empty($record['Datamodel'])) {
                $this->updateCustomDatamodelMappings($customDatamodel, $record);
            }
        }
        $this->info('Custom datamodels table updated');
    }

    private function updateCustomDatamodelMappings(CustomDatamodel $customDatamodel, $record)
    {
        CustomDatamodelMapping::updateOrCreate(
            [
                'custom_datamodel_id' => $customDatamodel->id,
            ],
            [
                'custom_datamodel_id' => $customDatamodel->id,
                'datamodel' => $record['Datamodel'],
                'mapping' => $record['Mapping'],
                'type' => $record['Data type'] ?? null
            ]
        );
    }
}
