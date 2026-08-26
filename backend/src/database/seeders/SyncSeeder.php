<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;

class SyncSeeder extends Seeder
{
    /**
     * Sync all the permissions and preferences.
     *
     * @return void
     */
    public function run()
    {
        $this->call(PermissionsSyncSeeder::class);
        $this->call(PreferencesSeeder::class);
        $this->call(ResourceLimitsSyncSeeder::class);
    }
}