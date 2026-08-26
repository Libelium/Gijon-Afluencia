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
        Schema::create('traffic_events_measurement_time', function (Blueprint $table) {
            $table->id();
            $table->string('source');
            $table->date('base_hour');
            $table->integer('processing_time_ms');
            $table->timestamps();

            $table->index(['source', 'base_hour'], 'traffic_events_measurement_time_source_base_hour_index');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('traffic_events_measurement_time');
    }
};
