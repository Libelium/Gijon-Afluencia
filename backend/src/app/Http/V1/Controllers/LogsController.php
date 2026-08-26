<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Controllers\Controller;
use App\Http\V1\Requests\Log\LogsTableDataRequest;
use App\Models\Log\Line;
use App\Repositories\LogsRepository;
use App\Http\V1\Resources\DefaultPaginationResource;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;


class LogsController extends Controller
{
    public function paginate(LogsTableDataRequest $request)
    {

        $log_lines = LogsRepository::paginate(Auth::user()->id, $request);

        $result = [
            'count' => $log_lines['count'],
            'rows' => $log_lines['rows'],
            'items' => $log_lines['rows'],
        ];

        return (new DefaultPaginationResource($result))->response();
    }
}
