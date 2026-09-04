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
        Schema::create('panels', function (Blueprint $table) {
            $table->id();
            $table->string('title')->nullable();
            $table->json('chart');
            $table->foreignId('dashboard_id')->references('id')->on('dashboards')->onDelete('cascade');
            $table->timestamps();
            $table->boolean('relative_time')->default(false);
            $table->jsonb('date_range')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('panels');
    }
};
