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
        Schema::table('entities', function (Blueprint $table) {
            $table->unique(['urn', 'fiware_scope_id'], 'unique_entity_index');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void {
        Schema::table('entities', function (Blueprint $table) {
            $table->dropUnique('unique_entity_index');
        });
    }
};
