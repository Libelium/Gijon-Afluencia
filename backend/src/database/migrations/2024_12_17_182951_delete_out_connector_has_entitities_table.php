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
        Schema::dropIfExists('out_connector_has_entities');
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::create('out_connector_has_entities', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('out_connector_id');
            $table->unsignedBigInteger('entity_id');
            $table->timestamps();
        });
    }
};
