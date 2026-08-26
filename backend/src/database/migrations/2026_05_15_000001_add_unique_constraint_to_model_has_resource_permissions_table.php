<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Keep only the oldest row per logical unique tuple, removing any duplicates
        // introduced before this constraint existed.
        DB::statement('
            DELETE FROM model_has_resource_permissions
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM model_has_resource_permissions
                GROUP BY model_id, model_type, resource_permission_id, resource_type, resource_id
            )
        ');

        Schema::table('model_has_resource_permissions', function (Blueprint $table) {
            $table->unique(
                ['model_id', 'model_type', 'resource_permission_id', 'resource_type', 'resource_id'],
                'mhrp_unique'
            );
        });
    }

    public function down(): void
    {
        Schema::table('model_has_resource_permissions', function (Blueprint $table) {
            $table->dropUnique('mhrp_unique');
        });
    }
};
