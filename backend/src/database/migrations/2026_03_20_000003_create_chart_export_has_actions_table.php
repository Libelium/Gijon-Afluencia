<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('chart_export_has_actions', function (Blueprint $table) {
            $table->foreignId('chart_export_id')->references('id')->on('chart_exports')->onDelete('cascade');
            $table->foreignId('action_id')->references('id')->on('actions')->onDelete('cascade');
            $table->primary(['chart_export_id', 'action_id']);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('chart_export_has_actions');
    }
};
