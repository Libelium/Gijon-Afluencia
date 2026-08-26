<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Carbon;

class File extends AuditableModel
{

    use HasFactory;

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = [
        'name',
        'description',
        'path',
        'filable_id',
        'filable_type',
        'type',
        'downloadable',
        'uuid'

    ];

    /**
     * Get all of the devices that are assigned this project.
     */
    public function filable()
    {
        return $this->morpheTo();
    }
}