<?php

namespace App\Models;

use Elastic\ScoutDriverPlus\Searchable;
use Illuminate\Database\Eloquent\Model;


class MarkdownFile extends AuditableModel
{
    use Searchable;

    protected $guarded = [];

    protected $fillable = [
        'route',
        'title',
        'content',
    ];

    public function getScoutKey()
    {
        return $this->route;
    }
}