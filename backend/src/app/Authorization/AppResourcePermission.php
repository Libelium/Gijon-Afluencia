<?php

namespace App\Authorization;

/**
 * The permissions a user can have over a resource (any kind of thing managed by the application)
 *
 * WARNING: be careful, all this values must be stored in the database too,
 * for that you have the seeder PermissionsSyncSeeder.php, which will read this enum
 * @package App\Models\Authorization
 */
enum AppResourcePermission: string
{
    case READ = 'read';
    case UPDATE = 'update';

    static function defaultPermissions(): array
    {
        return [
            self::READ,
            self::UPDATE,
        ];
    }

    static function fromValue(string $value): AppResourcePermission
    {
        return match ($value) {
            'read' => self::READ,
            'update' => self::UPDATE,
            default => throw new \Exception('Invalid permission value: ' . $value),
        };
    }
}
