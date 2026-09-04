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
            $table->string('command');
            $table->string('name');
            $table->text('description')->nullable();
            $table->string('operations');
            $table->string('data_types');
            $table->string('units');
            $table->timestamps();
            $table->integer('min')->nullable();
            $table->integer('max')->nullable();
            $table->boolean('internal')->default(false);
            $table->string('firmware_version')->nullable();
            $table->morphs('resource');
            $table->boolean('template')->default(false);
            $table->string('tab')->nullable();
            $table->string('datamodel')->nullable();
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
