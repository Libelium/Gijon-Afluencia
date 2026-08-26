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
        Schema::create('vehicle_emissions', function (Blueprint $table) {
            $table->id();
            $table->string('license_plate_number')->unique();
            $table->string('emission_category');
            $table->timestamps();
            $table->index('license_plate_number');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('vehicle_emissions');
    }
};
