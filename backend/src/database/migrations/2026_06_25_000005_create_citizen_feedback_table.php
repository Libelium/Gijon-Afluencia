<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('citizen_feedback', function (Blueprint $table) {
            $table->id();
            $table->string('topic'); // suggestion | survey | praise | complaint | app_issue
            $table->text('message');
            $table->boolean('anonymous')->default(false);
            $table->foreignId('user_id')->nullable()->constrained('users');
            $table->foreignId('organization_id')->nullable()->constrained('organizations');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('citizen_feedback');
    }
};
