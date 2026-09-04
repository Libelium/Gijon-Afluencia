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
        Schema::create('measure_series', function (Blueprint $table) {
            $table->id();
            $table->foreignId('entity_id')->references('id')->on('entities')->onDelete('cascade');
            $table->json('measure');
            $table->foreignId('serie_id')->references('id')->on('series')->onDelete('cascade');
            $table->boolean('visible')->default(true);
            $table->string('grouping_function')->nullable();
            $table->string('grouping_interval')->nullable();
            $table->integer('grouping_interval_value')->nullable();
            $table->timestamps();
            $table->json('period')->nullable();
            $table->double('grouping_function_value')->nullable();
            $table->jsonb('offset')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('measure_series');
    }
};
