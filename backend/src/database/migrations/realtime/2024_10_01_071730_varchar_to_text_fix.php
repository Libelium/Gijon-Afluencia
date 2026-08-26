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
            $table->text('value')->nullable()->change();
        });

        Schema::table('entity_commands', function (Blueprint $table) {
            $table->text('status')->nullable()->change();
            $table->text('info')->nullable()->change();
            $table->text('pending_value')->nullable()->change();
        });

        Schema::table('entity_properties', function (Blueprint $table) {
            $table->text('value')->nullable()->change();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('entity_properties', function (Blueprint $table) {
            $table->string('value')->nullable()->change();
        });

        Schema::table('entity_commands', function (Blueprint $table) {
            $table->string('status')->nullable()->change();
            $table->string('info')->nullable()->change();
            $table->string('pending_value')->nullable()->change();
        });

        Schema::table('entity_properties', function (Blueprint $table) {
            $table->string('value')->nullable()->change();
        });
    }
};
