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
        Schema::create('template_dashboards', function (Blueprint $table) {
            $table->id();
            $table->foreignId('dashboard_id')->references('id')->on('dashboards')->onDelete('cascade');
            $table->string('template_type');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('template_dashboards');
    }
};
