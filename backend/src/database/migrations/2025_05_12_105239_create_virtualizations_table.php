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
        Schema::create('virtualizations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('mapping_schema_id')->references('id')->on('mapping_schemas');
            $table->foreignId('destination_entity_id')->references('id')->on('entities');
            $table->morphs('virtualization');  
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('virtualizations');
    }
};
