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
        Schema::create('inactivity_alarm_conditions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('alarm_id')->constrained();
            $table->foreignId('entity_id')->constrained();
            $table->string('measure')->nullable();
            $table->integer('timeout_s');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('inactivity_alarm_conditions');
    }
};
