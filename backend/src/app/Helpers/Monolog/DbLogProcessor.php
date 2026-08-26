<?php

namespace App\Helpers\Monolog;

use Monolog\Processor\ProcessorInterface;

class DbLogProcessor implements ProcessorInterface
{
    /**
     * @return array The processed record
     */
    public function __invoke(array $record) {
        if(isset($record['context']['extra'])){
            //Move context->extra to extra column
            $record['extra'] = $record['context']['extra'];

            //Remove extra from contect column
            unset($record['context']['extra']);
        }


        return $record;
    }
}