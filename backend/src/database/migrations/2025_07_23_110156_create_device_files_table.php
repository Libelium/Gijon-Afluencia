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
        Schema::create('device_files', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('description')->nullable();
            $table->string('device_code')->references('code')->on('device_types')->onDelete('cascade');
            $table->string('fw_version')->default('all');
            $table->string('path');
            $table->string('extension');
            $table->boolean('downloadable')->default(false);
            $table->timestamps();
            $table->unique(['name', 'device_code', 'fw_version', 'extension'], 'name_per_devcode_fw_ext');
            $table->unique(['path', 'device_code', 'fw_version'], 'path_per_devcode_fw');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('device_files');
    }
};
