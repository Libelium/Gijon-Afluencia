<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('entity_properties', function (Blueprint $table) {
            $table->string('tenant')->default('platform');
            $table->string('scope')->default('/');
            $table->integer('entity_id')->unsigned()->default(0);
        });

        Schema::table('entity_commands', function (Blueprint $table) {
            $table->string('tenant')->default('platform');
            $table->string('scope')->default('/');
            $table->integer('entity_id')->unsigned()->default(0);
        });

        Schema::table('entity_relationships', function (Blueprint $table) {
            $table->string('tenant')->default('platform');
            $table->string('scope')->default('/');
            $table->integer('entity_id')->unsigned()->default(0);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('entity_properties', function (Blueprint $table) {
            $table->dropColumn('tenant');
            $table->dropColumn('scope');
            $table->dropColumn('entity_id');
        });

        Schema::table('entity_commands', function (Blueprint $table) {
            $table->dropColumn('tenant');
            $table->dropColumn('scope');
            $table->dropColumn('entity_id');
        });

        Schema::table('entity_relationships', function (Blueprint $table) {
            $table->dropColumn('tenant');
            $table->dropColumn('scope');
            $table->dropColumn('entity_id');
        });
    }
};
