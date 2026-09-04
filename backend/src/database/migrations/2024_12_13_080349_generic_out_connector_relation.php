<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('out_connectors_has_models', function (Blueprint $table) {
            $table->id();
            $table->foreignId('out_connector_id')->references('id')->on('out_connectors')->onDelete('cascade');
            $table->morphs('model');
            $table->timestamps();
        });

    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('out_connectors_has_models');
    }
};
