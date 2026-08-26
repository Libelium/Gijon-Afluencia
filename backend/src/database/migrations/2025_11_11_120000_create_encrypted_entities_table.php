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
        Schema::create('encrypted_entities', function (Blueprint $table) {
            $table->id();
            $table->string('entity_urn', 255);
            $table->string('tenant', 100);
            $table->string('scope', 100);
            $table->json('encrypted_attributes');
            $table->string('encryption_algorithm', 50)->default('AES-256-GCM');
            $table->string('datamodel_type', 100)->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('encrypted_entities');
    }
};
