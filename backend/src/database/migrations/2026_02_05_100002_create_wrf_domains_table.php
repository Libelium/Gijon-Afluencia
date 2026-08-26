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
        Schema::create('wrf_domains', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->json('upper_left_coordinates')->nullable(); // GeoJSON Point
            $table->json('lower_right_coordinates')->nullable(); // GeoJSON Point
            $table->foreignId('current_simulation_id')->nullable()->constrained('wrf_simulations')->onDelete('set null');
            $table->string('urn')->nullable();
            $table->foreignId('user_id')->constrained('users')->onDelete('cascade');
            $table->timestamps();
        });

        // Add foreign key to wrf_simulations after wrf_domains exists
        Schema::table('wrf_simulations', function (Blueprint $table) {
            $table->foreign('domain_id')->references('id')->on('wrf_domains')->onDelete('cascade');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('wrf_simulations', function (Blueprint $table) {
            $table->dropForeign(['domain_id']);
        });

        Schema::dropIfExists('wrf_domains');
    }
};
