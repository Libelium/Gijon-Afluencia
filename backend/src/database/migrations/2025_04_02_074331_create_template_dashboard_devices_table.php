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
        Schema::create('template_dashboard_devices', function (Blueprint $table) {
            $table->id();
            $table->foreignId('template_dashboard_id')->references('id')->on('template_dashboards')->onDelete('cascade');
            $table->foreignId('device_id')->references('id')->on('devices')->onDelete('cascade');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('template_dashboard_devices');
    }
};
