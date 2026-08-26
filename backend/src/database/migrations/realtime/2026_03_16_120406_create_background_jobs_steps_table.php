<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::connection($this->connection)->create('background_jobs_steps', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('user_id')->nullable()->index();
            $table->unsignedBigInteger('background_job_id')->index();
            $table->string('name')->nullable();   // step name; null = job-level event
            $table->string('status');
            $table->integer('order')->nullable();      // step position; null = job-level event
            $table->unsignedTinyInteger('progress')->nullable(); // 0-100
            $table->timestamps();
        });
    }

    public function down(): void
    {

        Schema::dropIfExists('background_jobs_steps');
    }
};
