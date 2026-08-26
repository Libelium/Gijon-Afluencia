<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Storage;

use App\Models\DeviceType;
use App\Models\DatamodelType;
use App\Models\CustomDatamodel;
use App\Models\CustomDatamodelMapping;
use League\Csv\Reader;

class updateCustomDatamodels extends Command
{
    /**
     * The name and signature of the console command.
     * --datamodel-type is a boolean flag.
     *
     * @var string
     */
    protected $signature = 'app:update-custom-datamodels
                            {--datamodel-type : Use DatamodelType instead of DeviceType}';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Update custom datamodels table';

    /**
     * Execute the console command.
     */

    public function handle()
    {
        $useDatamodelType = (bool) $this->option('datamodel-type');

        $files = Storage::disk('local')->files('CSV/devices');
        if (empty($files)) {
            $this->warn('No CSV files found in storage/app/CSV/devices');
            return self::SUCCESS;
        }

        foreach ($files as $file) {
            $this->info('Reading CSV file: ' . $file);
            $reader = Reader::createFromPath(storage_path('app/' . $file), 'r');
            $reader->setHeaderOffset(0);
            $records = $reader->getRecords();

            $prefix = explode('-', explode('/', $file)[2])[0];

            if ($useDatamodelType) {
                $datamodelType = DatamodelType::where('name', $prefix)->first();
                if (!$datamodelType) {
                    $this->warn("DatamodelType with name '{$prefix}' not found for file {$file}. Skipping.");
                    continue;
                }

                $resourceTypeClass = DatamodelType::class;
                $resourceId = $datamodelType->id;
                $this->info("Using DatamodelType '{$datamodelType->name}' (ID={$datamodelType->id}) for {$file}.");
            } else {
                $deviceType = DeviceType::where('code', $prefix)->first();
                if (!$deviceType) {
                    $this->warn("DeviceType with code '{$prefix}' not found for file {$file}. Skipping.");
                    continue;
                }

                $resourceTypeClass = DeviceType::class;
                $resourceId = $deviceType->id;
                $this->info("Using DeviceType '{$deviceType->code}' (ID={$deviceType->id}) for {$file}.");
            }

            $this->updateCustomDatamodels($records, $resourceTypeClass, $resourceId);
        }

        return self::SUCCESS;
    }


    private function updateCustomDatamodels($records, string $resourceTypeClass, int $resourceId): void
    {
        foreach ($records as $record) {
            $record['Min'] = $record['Min'] == 'N/A' ? null : (int)$record['Min'];
            $record['Max'] = $record['Max'] == 'N/A' ? null : (int)$record['Max'];
            $record['Internal'] = $record['Internal'] == 'Yes' ? true : false;

            if (isset($record['Template'])) {
                $record['Template'] = $record['Template'] == 'Yes' ? true : false;
            }

            $this->info('Updating ' . $record['Command']);
            $customDatamodel = CustomDatamodel::updateOrCreate(
                [
                    'resource_type' => $resourceTypeClass,
                    'resource_id'   => $resourceId,
                    'command'       => $record['Command']
                ],
                [
                    'resource_type'     => $resourceTypeClass,
                    'resource_id'       => $resourceId,
                    'command'           => $record['Command'],
                    'name'              => $record['Name'],
                    'description'       => $record['Description'],
                    'operations'        => $record['Operations'],
                    'data_types'        => $record['Data type'],
                    'units'             => $record['Units'],
                    'tab'               => $record['Tab'] ?? null,
                    'datamodel'         => $record['Datamodel'] ?? null,
                    'min'               => $record['Min'],
                    'max'               => $record['Max'],
                    'internal'          => $record['Internal'],
                    'firmware_version'  => $record['Firmware version'] ?? null,
                    'template'          => $record['Template'] ?? false,
                ]
            );
            if (!empty($record['Mapping']) && !empty($record['Datamodel'])) {
                $this->updateCustomDatamodelMappings($customDatamodel, $record);
            }
        }
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
