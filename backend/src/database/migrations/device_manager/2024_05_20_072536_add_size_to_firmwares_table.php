<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    protected $connection = 'device_manager';

    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('firmwares', function (Blueprint $table) {
            $table->integer('size')->default(0);;
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down()
    {
        Schema::table('firmwares', function (Blueprint $table) {
            $table->dropColumn('size');
        });
    }
};
