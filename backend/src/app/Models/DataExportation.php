<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class DataExportation extends AuditableModel
{
    protected $fillable = [
        'file',
        'payload',
    ];

    protected $casts = [
        'payload' => 'array',
    ];

    public function download()
    {
        return $this->morphOne(Download::class, 'downloadable');
    }

    public function s3_path()
    {
        return $this->file;
    }

    public function getMorphClass()
    {
        return $this->table;
    }

}