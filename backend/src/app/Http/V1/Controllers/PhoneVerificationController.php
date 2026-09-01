<?php

namespace App\Http\V1\Controllers;

use Aws\Sns\SnsClient;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\RateLimiter;
use App\Http\V1\Controllers\Controller;
use App\Models\PhoneVerificationCode;

class PhoneVerificationController extends Controller
{
    private const CODE_TTL_MINUTES   = 10;
    private const COOLDOWN_SECONDS   = 60;
    private const E164_REGEX         = '/^\+[1-9]\d{7,14}$/';

    /**
     * Brute-force budget for the confirmation code.
     *
     * The code is 6 digits and lives for 10 minutes, so without a limit the whole space is
     * walkable inside its validity window. Failed attempts are counted per user AND per phone
     * number — an attacker who can pick either one must not get a fresh budget by changing the
     * other. The route also carries a `throttle` middleware, which caps the request rate; this
     * counter is what caps the number of *wrong guesses*, and it survives IP rotation.
     */
    private const MAX_CONFIRM_ATTEMPTS = 5;
    private const CONFIRM_LOCKOUT_SECONDS = 900;

    public function send(Request $request)
    {
        $request->validate([
            'phone' => ['required', 'string', 'regex:' . self::E164_REGEX],
        ]);

        $user  = Auth::user();
        $phone = $request->input('phone');

        $existing = PhoneVerificationCode::where('user_id', $user->id)
            ->where('phone', $phone)
            ->first();

        if ($existing && $existing->isOnCooldown()) {
            return response()->json([
                'message'            => 'Please wait before requesting a new code.',
                'cooldown_remaining' => $existing->cooldownSecondsRemaining(),
            ], 429);
        }

        $code = str_pad(random_int(0, 999999), 6, '0', STR_PAD_LEFT);

        // Upsert — un registro por user+phone
        PhoneVerificationCode::updateOrCreate(
            ['user_id' => $user->id, 'phone' => $phone],
            [
                'code'       => $code,
                'verified'   => false,
                'expires_at' => now()->addMinutes(self::CODE_TTL_MINUTES),
                'sent_at'    => now(),
            ]
        );

        $this->sendSms($phone, "Your PID Gijón verification code is: {$code}");

        return response()->json([
            'message'    => 'Verification code sent.',
            'expires_in' => self::CODE_TTL_MINUTES * 60,
            'cooldown'   => self::COOLDOWN_SECONDS,
        ], 200);
    }

    public function confirm(Request $request)
    {
        $request->validate([
            'phone' => ['required', 'string', 'regex:' . self::E164_REGEX],
            'code'  => ['required', 'string', 'size:6'],
        ]);

        $user  = Auth::user();
        $phone = $request->input('phone');
        $code  = $request->input('code');

        $throttleKey = $this->confirmThrottleKey($user->id, $phone);

        if (RateLimiter::tooManyAttempts($throttleKey, self::MAX_CONFIRM_ATTEMPTS)) {
            return response()->json([
                'message'     => 'Too many verification attempts. Request a new code later.',
                'retry_after' => RateLimiter::availableIn($throttleKey),
            ], 429);
        }

        $record = PhoneVerificationCode::where('user_id', $user->id)
            ->where('phone', $phone)
            ->first();

        if (!$record) {
            RateLimiter::hit($throttleKey, self::CONFIRM_LOCKOUT_SECONDS);

            return response()->json(['message' => 'No verification code found for this number.'], 404);
        }

        if ($record->isExpired()) {
            RateLimiter::hit($throttleKey, self::CONFIRM_LOCKOUT_SECONDS);

            return response()->json(['message' => 'Verification code has expired.'], 422);
        }

        // hash_equals: the codes are equal-length digit strings, so a constant-time comparison
        // costs nothing and removes the timing signal.
        if (!hash_equals((string) $record->code, (string) $code)) {
            RateLimiter::hit($throttleKey, self::CONFIRM_LOCKOUT_SECONDS);

            return response()->json(['message' => 'Incorrect verification code.'], 422);
        }

        $record->update(['verified' => true]);

        // A verified number starts from a clean slate.
        RateLimiter::clear($throttleKey);

        return response()->json(['verified' => true], 200);
    }

    /**
     * Rate-limiter key for the confirmation attempts of one user on one phone number.
     *
     * The phone number is hashed so no personal data ends up in cache keys or logs.
     */
    private function confirmThrottleKey(int $userId, string $phone): string
    {
        return 'phone-verify:confirm:' . $userId . ':' . sha1($phone);
    }

    private function sendSms(string $phone, string $message): void
    {
        $client = new SnsClient([
            'version'     => 'latest',
            'region'      => env('SMS_AWS_REGION', 'eu-south-2'),
            'credentials' => [
                'key'    => env('SMS_AWS_KEY'),
                'secret' => env('SMS_AWS_SECRET'),
            ],
        ]);

        $messageAttributes = [
            'AWS.SNS.SMS.SMSType' => [
                'DataType'    => 'String',
                'StringValue' => 'Transactional',
            ],
        ];

        $senderId = env('SMS_FROM');
        if ($senderId) {
            $messageAttributes['AWS.SNS.SMS.SenderID'] = [
                'DataType'    => 'String',
                'StringValue' => $senderId,
            ];
        }

        $client->publish([
            'PhoneNumber'       => $phone,
            'Message'           => $message,
            'MessageAttributes' => $messageAttributes,
        ]);
    }
}
