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
        Schema::table('users', function (Blueprint $table) {
            $table->unsignedBigInteger('created_by')
                ->nullable();
        });

        $this->populateCreatedBy();

        Schema::table('users', function (Blueprint $table) {
            $table->foreign('created_by')
                  ->references('id')
                  ->on('users')
                  ->onDelete('set null');
        });

    }
    /**
     * Reverse the migrations.
     */
    
    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropForeign(['created_by']);
            $table->dropColumn('created_by');
        });
    }

    protected function populateCreatedBy(): void
    {
        DB::statement(/** @lang sql */ "
            UPDATE users
            SET created_by = org.admin
            FROM organizations AS org
            WHERE users.organization_id = org.id
              AND users.organization_id IS NOT NULL
        ");
    }
};
