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
        Schema::create('alarm_has_actions', function (Blueprint $table) {
            $table->foreignId('alarm_id')->references('id')->on('alarms');
            $table->foreignId('action_id')->references('id')->on('actions');
            $table->string('type')->nullable();
            $table->timestamps();

            $table->primary(['alarm_id', 'action_id']);
        });


    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('alarm_has_actions');
    }
};
