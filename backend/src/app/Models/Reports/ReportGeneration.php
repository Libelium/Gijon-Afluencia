<?php

namespace App\Models\Reports;

use Illuminate\Database\Eloquent\Model;

use App\Models\Download;

class ReportGeneration extends Model
{

    protected $fillable = [
        'report_id',
        'file',
        'created_at',
        'updated_at',
    ];

    public function download()
    {
        return $this->morphOne(Download::class, 'downloadable');
    }

    public function report()
    {
        return $this->belongsTo(Report::class);
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