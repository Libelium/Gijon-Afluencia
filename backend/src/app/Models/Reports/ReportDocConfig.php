<?php

namespace App\Models\Reports;

use Illuminate\Database\Eloquent\Model;
use App\Models\HtmlBlock;

class ReportDocConfig extends Model
{
    protected $fillable = [
        'user_id',
        'name',
        'config',
        'header_id',
        'footer_id'
    ];

    protected $casts = [
        'config' => 'array'
    ];

    public function reports()
    {
        return $this->hasMany(Report::class);
    }

    public function header()
    {
        return $this->belongsTo(HtmlBlock::class, 'header_id');
    }

    public function footer()
    {
        return $this->belongsTo(HtmlBlock::class, 'footer_id');
    }
}