<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Run the migrations.
     *
     * min/max hold the range of a command value, and some datamodels declare
     * uint32_t commands (e.g. r_lw_fcnt, max 4294967295) that overflow int4.
     */
    public function up(): void
    {
        DB::statement('ALTER TABLE custom_datamodels ALTER COLUMN min TYPE bigint');
        DB::statement('ALTER TABLE custom_datamodels ALTER COLUMN max TYPE bigint');
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        DB::statement('ALTER TABLE custom_datamodels ALTER COLUMN min TYPE integer');
        DB::statement('ALTER TABLE custom_datamodels ALTER COLUMN max TYPE integer');
    }
};
