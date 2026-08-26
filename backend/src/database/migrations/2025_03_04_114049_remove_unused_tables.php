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
        Schema::dropIfExists('user_entity_permissions');
        Schema::dropIfExists('out_connectors_has_entities');
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        // Never rollback, data is lost and tables should be unused
    }
};
