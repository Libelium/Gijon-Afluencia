<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Track the outcome of each ETL execution. Rows created before this
     * migration keep status NULL and are treated as successful (legacy).
     */
    public function up(): void
    {
        Schema::table('etl_executions', function (Blueprint $table) {
            $table->string('status', 20)->nullable()->after('params'); // started | success | failed
            $table->text('error')->nullable()->after('status');
            $table->timestamp('finished_at', 0)->nullable()->after('error');
            $table->index(['type', 'status'], 'etl_executions_type_status_index');
        });

        // The consumer looks a window up by type + params->>'start_date' + params->>'user_id'
        // before every run; without this expression index that is a sequential scan.
        DB::statement(
            "CREATE INDEX etl_executions_type_start_user_index ON etl_executions "
            . "(type, (params->>'start_date'), (params->>'user_id'))"
        );
    }

    public function down(): void
    {
        DB::statement('DROP INDEX IF EXISTS etl_executions_type_start_user_index');

        Schema::table('etl_executions', function (Blueprint $table) {
            $table->dropIndex('etl_executions_type_status_index');
            $table->dropColumn(['status', 'error', 'finished_at']);
        });
    }
};
