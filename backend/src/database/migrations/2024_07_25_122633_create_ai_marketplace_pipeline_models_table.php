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
        Schema::create('ai_marketplace_pipeline_models', function (Blueprint $table) {
            $table->id();
            $table->foreignId('ai_marketplace_pipeline_id')->references('id')->on('ai_marketplace_pipelines')->onDelete('cascade');
            $table->foreignId('ai_marketplace_model_id')->references('id')->on('ai_marketplace_models')->onDelete('cascade');
            $table->integer('order');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('ai_marketplace_pipeline_models');
    }
};
