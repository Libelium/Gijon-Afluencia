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
        Schema::create('custom_datamodels', function (Blueprint $table) {
            $table->id();
            $table->foreignId('device_type_id')->references('id')->on('device_types');
            $table->string('command');
            $table->string('name');
            $table->text('description')->nullable();
            $table->string('send_type');
            $table->string('operations');
            $table->string('data_types');
            $table->string('units');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('custom_datamodels');
    }
};
