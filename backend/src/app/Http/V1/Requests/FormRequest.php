<?php

namespace App\Http\V1\Requests;

use Illuminate\Foundation\Http\FormRequest as BaseFormRequest;

// Base class for the V1 form requests: it extends the framework's instead of shadowing it in
// the Illuminate\Foundation\Http namespace.
abstract class FormRequest extends BaseFormRequest
{
}
