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
        Schema::table('wrf_domains', function (Blueprint $table) {
            $table->foreignId('latest_automatic_simulation_id')->nullable()->constrained('wrf_simulations')->onDelete('set null');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('wrf_domains', function (Blueprint $table) {
            $table->dropForeign(['latest_automatic_simulation_id']);
            $table->dropColumn('latest_automatic_simulation_id');
        });
    }
};
