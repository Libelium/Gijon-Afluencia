<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('mqtt_users', function (Blueprint $table) {
            // add column organization_id as nullable foreign key
            $table->foreignId('organization_id')
                  ->nullable()
                  ->constrained('organizations') // o el nombre correcto de la tabla relacionada
                  ->nullOnDelete();

            // add index for organization_id
            $table->index('organization_id', 'idx_mqtt_users_organization_id');
        });
        
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('mqtt_users', function (Blueprint $table) {
            
            // drop foreign key and column organization_id
            $table->dropForeign(['organization_id']);
            $table->dropIndex(['organization_id']);
            $table->dropColumn('organization_id');
        });
    }
};
