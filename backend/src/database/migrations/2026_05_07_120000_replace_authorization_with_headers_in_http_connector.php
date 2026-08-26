<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('http_connector', function (Blueprint $table) {
            $table->jsonb('headers')->nullable();
        });

        DB::table('http_connector')
            ->whereNotNull('authorization')
            ->where('authorization', '!=', '')
            ->orderBy('id')
            ->each(function ($row) {
                DB::table('http_connector')
                    ->where('id', $row->id)
                    ->update([
                        'headers' => json_encode([
                            'Authorization' => 'Bearer ' . $row->authorization,
                        ]),
                    ]);
            });

        Schema::table('http_connector', function (Blueprint $table) {
            $table->dropColumn('authorization');
        });
    }

    public function down(): void
    {
        Schema::table('http_connector', function (Blueprint $table) {
            $table->string('authorization')->nullable();
        });

        DB::table('http_connector')
            ->whereNotNull('headers')
            ->orderBy('id')
            ->each(function ($row) {
                $headers = json_decode($row->headers, true) ?: [];
                $auth = $headers['Authorization'] ?? $headers['authorization'] ?? null;
                if ($auth) {
                    if (str_starts_with($auth, 'Bearer ')) {
                        $auth = substr($auth, 7);
                    }
                    DB::table('http_connector')
                        ->where('id', $row->id)
                        ->update(['authorization' => $auth]);
                }
            });

        Schema::table('http_connector', function (Blueprint $table) {
            $table->dropColumn('headers');
        });
    }
};
