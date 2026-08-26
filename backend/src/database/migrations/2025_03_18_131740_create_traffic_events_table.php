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
        Schema::create('traffic_events', function (Blueprint $table) {
            $table->id();
            $table->string('source');
            $table->string('event_type');
            $table->string('vehicle_type');
            $table->string('license_plate_country');
            $table->string('license_plate_number');
            $table->string('speed');
            $table->string('brand');
            $table->string('model');
            $table->string('color');
            $table->integer('user_id')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('traffic_events');
    }
};
