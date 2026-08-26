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
        Schema::table('traffic_events_measurement_time', function (Blueprint $table) {
            # convert base hour to from date to timestamp
            $table->timestamp('base_hour')->change();
            $table->unique(['source', 'base_hour'], 'source_base_hour_unique_constraint');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('traffic_events_measurement_time', function (Blueprint $table) {
            $table->dropUnique('source_base_hour_unique_constraint');
            $table->date('base_hour')->change();
        });
    }
};
