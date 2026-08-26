<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // entity_id → entities.id (the local mirror of the Incident NGSI-LD entity).
        Schema::create('incident_ratings', function (Blueprint $table) {
            $table->id();
            $table->foreignId('entity_id')->constrained('entities')->cascadeOnDelete();
            $table->foreignId('user_id')->nullable()->constrained('users');
            $table->unsignedTinyInteger('stars');
            $table->text('comment')->nullable();
            $table->jsonb('tags')->nullable();
            $table->timestamps();
            $table->unique(['entity_id', 'user_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('incident_ratings');
    }
};
