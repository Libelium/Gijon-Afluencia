<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        // Create pivot table for many-to-many relationship
        Schema::create('device_file_device_type', function (Blueprint $table) {
            $table->id();
            $table->foreignId('device_file_id')->constrained('device_files')->onDelete('cascade');
            $table->string('device_code');
            $table->timestamps();

            $table->unique(['device_file_id', 'device_code'], 'device_file_device_type_unique');
            $table->index('device_code');
        });

        // Migrate existing data from device_files.device_code to pivot table
        DB::statement('
            INSERT INTO device_file_device_type (device_file_id, device_code, created_at, updated_at)
            SELECT id, device_code, NOW(), NOW()
            FROM device_files
            WHERE device_code IS NOT NULL AND device_code != \'\'
        ');
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('device_file_device_type');
    }
};
