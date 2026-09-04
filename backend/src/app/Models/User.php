<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Laravel\Sanctum\HasApiTokens;
use Illuminate\Notifications\Notifiable;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Spatie\Permission\Traits\HasRoles;
use App\Authorization\HasResourcePermissions;
use App\Contracts\Limitable;
use App\Traits\Searchable;
use Spatie\Permission\Models\Role;
use OwenIt\Auditing\Contracts\Auditable as AuditableContract;
use OwenIt\Auditing\Auditable;
use App\Enums\UserStatus;


class User extends Authenticatable implements AuditableContract, Limitable
{
    // Sanctum
    use HasApiTokens;
    use Notifiable;
    use HasFactory;
    use HasRoles;
    use HasResourcePermissions;
    use Searchable;

    protected static array $searchable = ['name', 'email'];

    // Auditing
    use Auditable;

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = [
        'name',
        'email',
        'enabled',
        'last_activity',
        'keycloak_client_id',
        'organization_id',
        'created_by',
        'blocked_by_admin',
        'status',
    ];

    protected $casts = [
        'status' => UserStatus::class,
    ];

    protected $auditExclude = [
        'last_activity',
        'remember_token',
        'updated_at',
    ];

    public function preferences()
    {
        return $this->hasMany(\App\Models\Preferencable::class);
    }

    public function apiKey()
    {
        return $this->hasOne(\App\Models\ApiKey::class);
    }

    public function organization(): BelongsTo
    {
        return $this->belongsTo(\App\Models\Organization::class);
    }

    public function isOrganizationAdmin()
    {
        return $this->organization->admin == $this->id;
    }

    public function roles()
    {
        return $this->morphToMany(Role::class, 'model', 'model_has_roles');
    }

    public function resourceLimits()
    {
        return $this->hasMany(UserResourceLimit::class);
    }

    public function creator(): BelongsTo
    {
        return $this->belongsTo(self::class, 'created_by');
    }

    public static function countByUser(int $creatorUserId): int
    {
        return static::where('created_by', $creatorUserId)->count();
    }

    public static function countByUsers($creatorUserIds): int
    {
        return static::whereIn('created_by', $creatorUserIds)->count();
    }

}
