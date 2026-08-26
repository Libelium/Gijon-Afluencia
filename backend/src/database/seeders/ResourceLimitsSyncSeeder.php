<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use App\Models\ResourceLimit;

class ResourceLimitsSyncSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run(): void
    {
        // Use updateOrCreate to prevent duplicate entries on re-seeding.
        // This will create the record if it doesn't exist, or update it if it does.
        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\Dashboard::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\EntityGroup::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\Reports\Report::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\Workspace::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\Alarm::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\InConnector::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\OutConnectors\OutConnector::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\AIMarketplacePipeline::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\User::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \Spatie\Permission\Models\Role::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

        ResourceLimit::updateOrCreate(
            ['resource_type' => \App\Models\HomeLayout::class],
            [
                'value' => 500,
                'created_at' => now(),
                'updated_at' => now(),
            ]
        );

    }
}
