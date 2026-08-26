<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up()
    {
        Schema::create('bootstrap_logs', function (Blueprint $table) {
            $table->id();
            $table->string('serial')->index();
            $table->string('type');
            $table->jsonb('profiles');
            $table->timestamps();
            $table->unique('serial', 'uq_bootstrap_logs_serial');
        });
    }

    public function down()
    {
        Schema::dropIfExists('bootstrap_logs');
    }
};
