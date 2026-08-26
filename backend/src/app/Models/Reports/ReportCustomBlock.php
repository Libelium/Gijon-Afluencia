<?php

namespace App\Models\Reports;

use Illuminate\Database\Eloquent\Model;
use App\Models\Reports\Report;

class ReportCustomBlock extends Model
{
    protected $table = 'report_has_custom_blocks';

    protected $fillable = [
        'type',
        'position',
        'custom_blockable_id',
        'custom_blockable_type',
        'report_id'
    ];

    public function getMorphClass()
    {
        return $this->table;
    }

    public function custom_blockable()
    {
        return $this->morphTo();
    }

    public function report()
    {
        return $this->belongsTo(Report::class);
    }
}