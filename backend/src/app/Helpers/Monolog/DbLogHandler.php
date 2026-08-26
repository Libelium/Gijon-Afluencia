<?php

namespace App\Helpers\Monolog;

use App\Models\Log\Line;
use Monolog\Logger;
use Monolog\Handler\AbstractProcessingHandler;

//Models

class DbLogHandler extends AbstractProcessingHandler
{

    public function __construct($level = Logger::DEBUG, bool $bubble = true)
    {
        parent::__construct($level, $bubble);
    }

    protected function write(array $record): void
    {
        Line::create([
            'message' => $record['message'],
            'channel' => $record['channel'],
            'level' => $record['level'],
            'level_name' => $record['level_name'],
            'datetime' => $record['datetime'],
            'context' => $record['context'],
            'extra' => $record['extra'],
        ]);
    }

}
