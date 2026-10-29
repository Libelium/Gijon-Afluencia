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
        // Brokers that authenticate each device by certificate (mutual TLS) instead of password.
        Schema::table('mqtt_connector', function (Blueprint $table) {
            $table->text('clientCert')->nullable();
            $table->text('clientKey')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('mqtt_connector', function (Blueprint $table) {
            $table->dropColumn(['clientCert', 'clientKey']);
        });
    }
};
