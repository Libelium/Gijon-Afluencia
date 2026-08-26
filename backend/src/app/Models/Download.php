<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Download extends AuditableModel
{
    protected $fillable = [
        'downloadable_id',
        'downloadable_type',
        'user_id',
        'downloaded',
        "file_name",
        "file_extension",
        "status",

    ];


    public function downloadable()
    {
        return $this->morphTo();
    }

    public function getMorphClass()
    {
        return $this->table;
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}   