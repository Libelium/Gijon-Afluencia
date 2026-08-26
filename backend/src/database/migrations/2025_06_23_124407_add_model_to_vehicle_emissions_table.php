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
        Schema::table('vehicle_emissions', function (Blueprint $table) {
            $table->string('model')->nullable();
            $table->index('model', 'vehicle_emissions_model_index');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('vehicle_emissions', function (Blueprint $table) {
            $table->dropIndex('vehicle_emissions_model_index');
            $table->dropColumn('model');
        });
    }
};
