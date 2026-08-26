<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Add the one grid mapping schema.
     */
    public function up(): void
    {
        DB::table('mapping_schemas')->insert([
            'name' => 'OneGrid',
            'map' => json_encode([
                "type" => "table",
                "mapping" => [
                    ["source_attr" => "rssi", "target_attr" => "mi_Atr_personalizada_para_rssi"],
                ],
                "variables" => ["source_attr", "target_attr"],
                "include_non_translated" => true
            ]),
            'created_at' => now(),
            'updated_at' => now(),
        ]);
    }

    /**
     * Reverse the migration.
     */
    public function down(): void
    {
        DB::table('mapping_schemas')->where('name', 'OneGrid')->delete();
    }
};
