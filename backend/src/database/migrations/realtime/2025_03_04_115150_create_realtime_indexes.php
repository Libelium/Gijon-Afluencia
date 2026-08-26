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
        Schema::table('entity_properties', function (Blueprint $table) {
            $table->index(['entity_id']);
            $table->index(['urn', 'tenant', 'scope']);
        });

        Schema::table('entity_commands', function (Blueprint $table) {
            $table->index(['entity_id']);
            $table->index(['urn', 'tenant', 'scope', 'pending']);
        });

        Schema::table('entity_relationships', function (Blueprint $table) {
            $table->index(['entity_id']);
            $table->index(['urn', 'tenant', 'scope']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void {}
};
