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
        Schema::create('multidimensional_series', function (Blueprint $table) {
            $table->id();
            $table->foreignId('serie_id')->references('id')->on('series')->onDelete('cascade');
            $table->integer('axis');
            $table->foreignId('dimension_serie_id')->references('id')->on('series')->onDelete('cascade');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('multidimensional_series');
    }
};
