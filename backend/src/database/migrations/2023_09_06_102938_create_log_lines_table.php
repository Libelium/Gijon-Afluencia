<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateLogLinesTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('log_lines', function (Blueprint $table) {
            $table->increments('id');
            $table->text('message')->nullable();
            $table->string('level_name', 20);
            $table->dateTime('datetime')->nullable();
            $table->jsonb('extra')->nullable();
            $table->timestamps();
            $table->string('resource_type')->nullable();
            $table->integer('resource_id')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('log_lines');
    }
}
