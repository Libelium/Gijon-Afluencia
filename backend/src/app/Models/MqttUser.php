<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Support\Facades\Hash;

class MqttUser extends AuditableModel
{
    use HasFactory;

    protected $table = 'mqtt_users';

    protected $fillable = [
        'username',
        'password_hash',
        'is_admin',
        'is_active',
        'organization_id',
    ];

    protected $casts = [
        'is_admin' => 'boolean',
        'is_active' => 'boolean',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    protected $hidden = [
        'password_hash',
        // Dropped by migration; still listed so an installation that has not migrated yet
        // cannot serialise or audit them.
        'password_encrypted',
        'password_salt',
    ];

    protected $auditExclude = [
        'password_hash',
        'password_encrypted',
        'password_salt',
    ];

    // Relationships
    public function acls()
    {
        return $this->hasMany(MqttAcl::class, 'user_id');
    }

    public function organization()
    {
        return $this->belongsTo(Organization::class);
    }

    // Helper Methods
    // Only the derivation is stored (Hash, with its own salt): the broker credential only ever
    // needs verifying, nobody needs it in clear.
    private function setPassword($plainPassword)
    {
        $this->password_hash = Hash::make($plainPassword);
    }

    public function verifyPassword($password)
    {
        return Hash::check($password, $this->password_hash);
    }

    public function deactivate()
    {
        $this->is_active = false;
        $this->save();
        return $this;
    }

    public function activate()
    {
        $this->is_active = true;
        $this->save();
        return $this;
    }

    public function addAcl($topic, $permission)
    {
        return $this->acls()->create([
            'topic' => $topic,
            'rw' => $permission,
        ]);
    }

    public function removeAcl($topic)
    {
        return $this->acls()->where('topic', $topic)->delete();
    }

    public function hasPermissionForTopic($topic, $permission)
    {
        return $this->acls()
            ->where('topic', $topic)
            ->where(function ($query) use ($permission) {
                $query->where('rw', $permission)
                    ->orWhere('rw', 3); // read+write
            })
            ->exists();
    }

    // Static methods for user management
    public static function createMqttUser($username, $password, $organization_id, $isAdmin = false)
    {
        $user = new self();
        $user->username = $username;
        $user->is_admin = $isAdmin;
        $user->is_active = true;
        $user->organization_id = $organization_id;
        $user->setPassword($password);
        $user->save();

        return $user;
    }

    public static function findByUsername($username)
    {
        return self::where('username', $username)->where('is_active', true)->get();
    }

    public static function getAllWithAclCount($includeInactive = false)
    {
        $query = self::withCount('acls');

        if (!$includeInactive) {
            $query->where('is_active', true);
        }

        return $query->orderBy('created_at', 'desc')->get();
    }
}
