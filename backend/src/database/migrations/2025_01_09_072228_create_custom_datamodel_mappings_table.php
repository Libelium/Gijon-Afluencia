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
        Schema::create('custom_datamodel_mappings', function (Blueprint $table) {
            $table->id();
            $table->foreignId('custom_datamodel_id')->references('id')->on('custom_datamodels')->onDelete('cascade');
            $table->string('datamodel');
            $table->string('mapping');
            $table->string('type')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('custom_datamodel_mappings');
    }
};
