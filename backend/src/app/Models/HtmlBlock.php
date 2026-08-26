<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use App\Models\Reports\ReportCustomBlock;

class HtmlBlock extends AuditableModel
{
    protected $fillable = [
        'user_id',
        'name',
        'content',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function custom_blocks()
    {
        // custom blockable as block
        return $this->morphMany(ReportCustomBlock::class, 'custom_blockable');
    }
}