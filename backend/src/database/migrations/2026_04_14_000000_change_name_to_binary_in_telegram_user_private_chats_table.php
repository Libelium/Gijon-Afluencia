<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        DB::statement('CREATE EXTENSION IF NOT EXISTS pgcrypto');
        DB::statement('ALTER TABLE telegram_user_private_chats ALTER COLUMN name TYPE bytea USING name::bytea');
        DB::statement('ALTER TABLE telegram_user_private_chats ALTER COLUMN name DROP NOT NULL');
    }

    public function down(): void
    {
        DB::statement('ALTER TABLE telegram_user_private_chats ALTER COLUMN name TYPE varchar USING convert_from(name, \'UTF8\')');
    }
};
