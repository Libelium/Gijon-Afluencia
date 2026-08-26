<?php

namespace App\Exceptions;

use Exception;

class EntityAlreadyExistException extends Exception
{
    protected $customMessage;

    public function __construct(string $customMessage = "Entity already exists")
    {
        parent::__construct($customMessage);
        $this->customMessage = $customMessage;
    }

    public function getCustomMessage()
    {
        return $this->customMessage;
    }
}
