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
        Schema::create('firmwares', function (Blueprint $table) {
            $table->id();
            $table->integer('device_type_id');
            $table->uuid('uuid');
            $table->string('version', 50);
            $table->string('file_name', 100);
            $table->string('crc', 16)->nullable();
            $table->string('notes', 250)->nullable();
            $table->string('type', 25);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('firmwares');
    }
};
