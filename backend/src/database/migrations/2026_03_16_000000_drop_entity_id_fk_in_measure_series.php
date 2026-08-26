<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('measure_series', function (Blueprint $table) {
            $table->dropForeign(['entity_id']);
            $table->bigInteger('entity_id')->change(); // signed to allow -1 as dynamic sentinel
        });
    }

    public function down(): void
    {
        Schema::table('measure_series', function (Blueprint $table) {
            $table->unsignedBigInteger('entity_id')->change();
            $table->foreign('entity_id')->references('id')->on('entities')->onDelete('cascade');
        });
    }
};
