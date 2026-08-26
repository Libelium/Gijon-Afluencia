<?php

namespace App\Models\ChartExports;

use Illuminate\Database\Eloquent\Model;
use App\Models\Download;

class ChartExportGeneration extends Model
{
    protected $fillable = [
        'chart_export_id',
        'file',
        'created_at',
        'updated_at',
    ];

    public function download()
    {
        return $this->morphOne(Download::class, 'downloadable');
    }

    public function chartExport()
    {
        return $this->belongsTo(ChartExport::class);
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
