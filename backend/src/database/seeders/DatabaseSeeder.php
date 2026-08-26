<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    /**
     * Seed the application's database.
     *
     * @return void
     */
    public function run()
    {
        $this->call(DeviceTypesSeeder::class);
        $this->call(SyncSeeder::class);
        $this->call(SaasOrganizationsSeeder::class);
    }
}