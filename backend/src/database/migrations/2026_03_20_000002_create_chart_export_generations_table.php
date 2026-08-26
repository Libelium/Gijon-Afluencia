<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('chart_export_generations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('chart_export_id')->references('id')->on('chart_exports')->onDelete('cascade');
            $table->string('file', 1024)->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('chart_export_generations');
    }
};
