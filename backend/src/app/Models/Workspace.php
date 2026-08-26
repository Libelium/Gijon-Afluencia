<?php
namespace App\Models;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use App\Models\User;
use App\Models\Authorization\ModelHasResourcePermission;


class Workspace extends AuditableModel implements Limitable
{
    protected $table = 'workspaces';

    protected $fillable = [
        'name',
        'description',
        'user_id',
        'collaborative',
    ];

    protected $hidden = [

    ];

    public function admin()
    {
        return $this->belongsTo(User::class, 'user_id');
    }

    public function users()
    {
        return $this->belongsToMany(User::class, 'workspace_has_users');
    }

    public function resources()
    {
        return $this->morphMany(ModelHasResourcePermission::class, 'model');
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }

    public function getMorphClass()
    {
        // table name
        return 'workspaces';
    }
}
