<?php

namespace App\Enums;

enum UserStatus: string
{
    case Active    = 'active';
    case Deleted   = 'deleted';
    case Suspended = 'suspended';
    case Blocked   = 'blocked';
}
