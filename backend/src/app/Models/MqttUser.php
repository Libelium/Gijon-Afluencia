<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;
use Illuminate\Encryption\Encrypter;
use Illuminate\Support\Facades\Crypt;

class MqttUser extends AuditableModel
{
    use HasFactory;

    protected $table = 'mqtt_users';

    protected $fillable = [
        'username',
        'password_hash',
        'password_encrypted',
        'password_salt',
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
    private function setPasswords($plainPassword)
    {
        $salt = Str::random(32);

        $this->password_hash = Hash::make($plainPassword);

        $this->password_salt = $salt;
        $this->password_encrypted = $this->encryptPasswordWithSalt($plainPassword, $salt);
    }

    public function getDecryptedPassword()
    {
        if (!$this->password_encrypted || !$this->password_salt) {
            return null;
        }

        try {
            return $this->decryptPasswordWithSalt($this->password_encrypted, $this->password_salt);
        } catch (\Exception $e) {
            return 'Unable to decrypt';
        }
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

    // Encryption helpers (similar to Python implementation)
    private function encryptPasswordWithSalt($password, $salt)
    {
        $masterKey = config('mqtt.encryption_key');

        // Create a key derivation similar to Python's PBKDF2HMAC
        $derivedKey = hash_pbkdf2('sha256', $masterKey, $salt, 100000, 32, true);

        // Use Laravel's encryption with the derived key
        $encrypter = new Encrypter($derivedKey, 'aes-256-cbc');
        $encrypted = $encrypter->encrypt($password);

        return base64_encode($encrypted);
    }

    private function decryptPasswordWithSalt($encryptedPassword, $salt)
    {
        $masterKey = config('mqtt.encryption_key');

        $derivedKey = hash_pbkdf2('sha256', $masterKey, $salt, 100000, 32, true);

        $encrypter = new Encrypter($derivedKey, 'aes-256-cbc');
        $encryptedBytes = base64_decode($encryptedPassword);

        return $encrypter->decrypt($encryptedBytes);
    }

    // Static methods for user management
    public static function createMqttUser($username, $password, $organization_id, $isAdmin = false)
    {
        $user = new self();
        $user->username = $username;
        $user->is_admin = $isAdmin;
        $user->is_active = true;
        $user->organization_id = $organization_id;
        $user->setPasswords($password);
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
