<?php

namespace App\Helpers\Monolog;

use Monolog\Logger;


class DbLog
{
    /**
     * Create a custom Monolog instance.
     *
     * @param  array $config
     * @return \Monolog\Logger
     */
    public function __invoke(array $config)
    {
        $level = Logger::toMonologLevel($config['level']);

        $a_handlers = [
            new DbLogHandler($level, true)
        ];
        $a_processors = [
            new DbLogProcessor()
        ];

        return new Logger('custom_db', $a_handlers, $a_processors);
    }
}