<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('entity_groups', function (Blueprint $table) {
            $table->foreignId('entity_id')
                ->nullable()
                ->unique()
                ->references('id')->on('entities')->onDelete('cascade');
            $table->string('type')->nullable();
        });

        DB::statement("
            ALTER TABLE entity_groups
            ADD CONSTRAINT chk_linked_entity_columns
            CHECK (
                (entity_id IS NULL AND type IS NULL)
                OR
                (entity_id IS NOT NULL AND type IS NOT NULL)
            )
        ");
    }

    public function down(): void
    {
        DB::statement("ALTER TABLE entity_groups DROP CONSTRAINT IF EXISTS chk_linked_entity_columns");

        Schema::table('entity_groups', function (Blueprint $table) {
            $table->dropForeign(['entity_id']);
            $table->dropUnique(['entity_id']);
            $table->dropColumn(['entity_id', 'type']);
        });
    }
};
