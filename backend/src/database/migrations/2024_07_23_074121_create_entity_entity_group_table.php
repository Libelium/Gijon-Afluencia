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
        Schema::create('entity_entity_group', function (Blueprint $table) {
            $table->timestamps();
            $table->foreignId('entity_id')->references('id')->on('entities')->onDelete('cascade');
            $table->foreignId('entity_group_id')->references('id')->on('entity_group')->onDelete('cascade');
            $table->primary(['entity_id', 'entity_group_id']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('entity_entity_group');
    }
};
