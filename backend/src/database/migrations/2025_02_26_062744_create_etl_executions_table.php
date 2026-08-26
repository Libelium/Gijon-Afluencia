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
        Schema::create('etl_executions', function (Blueprint $table) {
            $table->id();
            $table->string('type'); // etl type
            $table->integer('user_id')->nullable();
            $table->date('execution_date')->nullable();
            $table->jsonb('params')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('etl_executions');
    }
};
