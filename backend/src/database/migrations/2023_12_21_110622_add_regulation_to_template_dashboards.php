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
        Schema::table('template_dashboards', function (Blueprint $table) {
            // add regulation_id column
            $table->foreignId('regulation_id')->nullable()->references('id')->on('regulations')->onDelete('cascade');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('template_dashboards', function (Blueprint $table) {
            // drop regulation_id column
            $table->dropColumn('regulation_id');
        });
    }
};
