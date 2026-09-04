<?php

namespace App\Exceptions;

use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Foundation\Exceptions\Handler as ExceptionHandler;
use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpKernel\Exception\HttpException;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;
use Throwable;
use App\Exceptions\EntityAlreadyExistException;

class Handler extends ExceptionHandler
{
    /**
     * The list of the inputs that are never flashed to the session on validation exceptions.
     *
     * @var array<int, string>
     */
    protected $dontFlash = [
        'current_password',
        'password',
        'password_confirmation',
    ];

    /**
     * Register the exception handling callbacks for the application.
     */
    public function register(): void
    {
        $this->reportable(function (Throwable $e) {
            //
        });
    }

    /**
     * Determine if the exception should be reported.
     *
     * This project is full API, so we dont want to return html, we always
     * return json (as we always accept json)
     */
    public function shouldReturnJson($request, $exception): bool
    {
        return true;
    }

    /*
     * Exceptions should return an error message, not a stack trace,
     * but the result code should not be modified.
     *
     * In production mode (APP_DEBUG=false), sensitive error details are hidden
     * and generic messages are shown to prevent information disclosure.
     */
    public function render($request, Throwable $exception)
    {
        $response = parent::render($request, $exception);
        $statusCode = $response->getStatusCode();

        if ($exception instanceof ValidationException || $exception instanceof HttpResponseException) {
            $payload = json_decode((string) $response->getContent(), true);

            if (is_array($payload)) {
                $this->writeJson($response, $payload + ['code' => $statusCode]);
            }

            return $response;
        }

        $this->writeJson($response, [
            'message' => $this->getSecureMessage($exception, $statusCode),
            'code' => $statusCode,
        ]);

        return $response;
    }

    /**
     * The escaping flags are set explicitly: Illuminate\Http\JsonResponse overrides Symfony's
     * default with 0, and the preserved ValidationException body echoes back user input.
     */
    private function writeJson($response, array $payload): void
    {
        $flags = JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT;

        if ($response instanceof JsonResponse) {
            $response->setEncodingOptions($flags);
            $response->setData($payload);

            return;
        }

        $response->setContent(json_encode($payload, $flags));
    }

    /**
     * Get a secure error message based on the environment and exception type.
     *
     * In debug mode, returns the actual exception message.
     * In production, returns generic messages for most exceptions to prevent
     * information disclosure, while allowing safe messages for specific exception types.
     */
    private function getSecureMessage(Throwable $exception, int $statusCode): string
    {
        // In debug mode, show the actual message
        if (config('app.debug')) {
            return $exception->getMessage();
        }

        // These exception types have user-safe messages by design
        if ($this->isSafeException($exception)) {
            return $exception->getMessage();
        }

        // For HTTP exceptions, use the message if it's explicitly set
        if ($exception instanceof HttpException && $exception->getMessage()) {
            return $exception->getMessage();
        }

        // Return generic messages based on status code for all other exceptions
        return $this->getGenericMessage($statusCode);
    }

    /**
     * Determine if the exception type is safe to expose its message to users.
     */
    private function isSafeException(Throwable $exception): bool
    {
        // ModelNotFoundException is deliberately out: its message leaks the model class and id.
        // HttpResponseException is out too, render() resolves it earlier and keeps its body.
        return $exception instanceof ValidationException
            || $exception instanceof AuthenticationException
            || $exception instanceof AuthorizationException
            || $exception instanceof NotFoundHttpException
            || $exception instanceof EntityAlreadyExistException;
    }

    /**
     * Get a generic, user-friendly error message based on HTTP status code.
     */
    private function getGenericMessage(int $statusCode): string
    {
        return match ($statusCode) {
            400 => 'Bad request.',
            401 => 'Unauthenticated.',
            403 => 'Forbidden.',
            404 => 'Resource not found.',
            405 => 'Method not allowed.',
            422 => 'Validation error.',
            429 => 'Too many requests.',
            500 => 'An internal server error occurred.',
            502 => 'Bad gateway.',
            503 => 'Service unavailable.',
            504 => 'Gateway timeout.',
            default => 'An error occurred.',
        };
    }
}
