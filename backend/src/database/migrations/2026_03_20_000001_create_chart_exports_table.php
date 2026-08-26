<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('chart_exports', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->text('description')->nullable();
            $table->foreignId('panel_id')->references('id')->on('panels')->onDelete('cascade');
            $table->foreignId('dashboard_id')->references('id')->on('dashboards')->onDelete('cascade');
            $table->foreignId('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->string('format', 10)->default('png');
            $table->integer('image_width')->default(1600);
            $table->integer('image_height')->default(600);
            $table->jsonb('period')->nullable();
            $table->json('date_range')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('chart_exports');
    }
};
