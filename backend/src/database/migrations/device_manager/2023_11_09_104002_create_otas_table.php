<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    protected $connection = 'device_manager';

    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('otas', function (Blueprint $table) {
            $table->id();
            $table->foreignId('firmware_id')->constrained('firmwares');
            $table->string('device_serial');
            $table->string('status')->nullable();
            $table->string('destination')->nullable();
            $table->integer('remaining_retries')->nullable();
            $table->timestamps();
        });

        Schema::create('ota_reports', function (Blueprint $table) {
            $table->id();
            $table->foreignId('ota_id')->constrained('otas');
            $table->integer('dev_report')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('ota_reports');
        Schema::dropIfExists('otas');
    }
};
