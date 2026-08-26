<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;

class VehicleEmissionsSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $path = database_path('seeders/export_distintivo_ambiental.txt');

        if (!file_exists($path)) {
            $this->command->error("File not found: $path");
            return;
        }

        $handle = fopen($path, 'r');
        if (!$handle) {
            $this->command->error("Failed to open file: $path");
            return;
        }

        $batchSize = 10000;
        $vehicles = [];
        $inserted = 0;

        # count all vehicles in database to skip them
        $existingVehicles = DB::table('vehicle_emissions')->count();

        $skipped = 0;

        while (($line = fgets($handle)) !== false) {
            $line = trim($line);

            if (empty($line) || str_starts_with($line, 'MATRICULA')) {
                continue;
            }

            $parts = explode('|', $line);
            if (count($parts) !== 2) continue;

            if ($skipped < $existingVehicles) {
                $skipped++;
                continue;
            }

            [$licensePlate, $emissionCategory] = $parts;

            // Hash the license plate using SHA-256. This makes the data anonymous
            // but still allows for direct lookups, as the same input will always
            // produce the same output.
            $hashedLicensePlate = hash('sha256', $licensePlate);

            $vehicles[] = [
                'license_plate_number' => $hashedLicensePlate,
                'emission_category' => $emissionCategory,
                'created_at' => now(),
                'updated_at' => now(),
            ];
            

            if (count($vehicles) >= $batchSize) {
                $this->command->info("Seeding $inserted vehicle emission records...");

                try {
                    DB::table('vehicle_emissions')->insert($vehicles);
                } catch (\Throwable $e) {
                    $this->command->info("Failed to insert records");
                }
                $inserted += count($vehicles);
                $vehicles = [];
                gc_collect_cycles(); // Free memory
            }
        }

        if (!empty($vehicles)) {
            DB::table('vehicle_emissions')->insert($vehicles);
            $inserted += count($vehicles);
        }

        fclose($handle);

        $this->command->info("Seeded $inserted vehicle emission records successfully.");
    }
}
