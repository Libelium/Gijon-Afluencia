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
        Schema::create('out_connectors', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('type');
            $table->string('status');
            $table->foreignId('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->date('last_connection')->nullable();
            $table->morphs('connectable');
            $table->timestamps();
            $table->integer('retries')->default(0);
            $table->boolean('use_readable_names')->default(false);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('out_connectors');
    }
};
