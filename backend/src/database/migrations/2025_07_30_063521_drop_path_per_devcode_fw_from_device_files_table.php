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
        Schema::table('device_files', function (Blueprint $table) {
            $table->dropUnique('path_per_devcode_fw');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('device_files', function (Blueprint $table) {
            $table->unique(['path', 'device_code', 'fw_version'], 'path_per_devcode_fw');
        });
    }
};
