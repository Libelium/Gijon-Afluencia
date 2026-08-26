<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use App\Models\Reports\Report;

class Folder extends Model
{
    protected $fillable = [
        'user_id',
        'name',
        'description',
        'parent_id',
        'color',
    ];

    public function reports()
    {
        return $this->hasMany(Report::class);
    }

    public function parent()
    {
        return $this->belongsTo(Folder::class, 'parent_id');
    }

    public function children()
    {
        return $this->hasMany(Folder::class, 'parent_id');
    }

    public function tags()
    {
        return $this->belongsToMany(Tag::class, 'folder_tag');
    }

    /**
     * The folder ZIP export reuses the shared polymorphic Download model.
     * The queues-consumer job uploads the archive to this conventional path
     * and creates/updates the Download row pointing at this folder.
     */
    public function download()
    {
        return $this->morphOne(Download::class, 'downloadable');
    }

    public function s3_path()
    {
        return 'folders/' . $this->id . '/export.zip';
    }

    public function getMorphClass()
    {
        return $this->getTable();
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
