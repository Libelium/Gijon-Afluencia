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
        Schema::create('in_connectors_has_entities', function (Blueprint $table) {
            $table->id();
            $table->foreignId('in_connector_id')->references('id')->on('in_connectors')->onDelete('cascade');
            $table->foreignId('entity_id')->references('id')->on('entities')->onDelete('cascade');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('in_connectors_has_entities');
    }
};
