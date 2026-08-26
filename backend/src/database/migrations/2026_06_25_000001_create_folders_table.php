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
        Schema::create('folders', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('user_id');
            $table->string('name');
            $table->text('description')->nullable();
            // Self-reference for nesting. On parent deletion, children float up to
            // root (set null) rather than being deleted.
            $table->unsignedBigInteger('parent_id')->nullable();
            $table->string('color', 30)->nullable();
            $table->timestamps();

            $table->foreign('parent_id')
                ->references('id')
                ->on('folders')
                ->onDelete('set null');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('folders');
    }
};
