<?php

namespace App\Http\V1\Controllers;

use Aws\Sns\SnsClient;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use App\Http\V1\Controllers\Controller;
use App\Models\PhoneVerificationCode;

class PhoneVerificationController extends Controller
{
    private const CODE_TTL_MINUTES   = 10;
    private const COOLDOWN_SECONDS   = 60;
    private const E164_REGEX         = '/^\+[1-9]\d{7,14}$/';

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

        $record = PhoneVerificationCode::where('user_id', $user->id)
            ->where('phone', $phone)
            ->first();

        if (!$record) {
            return response()->json(['message' => 'No verification code found for this number.'], 404);
        }

        if ($record->isExpired()) {
            return response()->json(['message' => 'Verification code has expired.'], 422);
        }

        if ($record->code !== $code) {
            return response()->json(['message' => 'Incorrect verification code.'], 422);
        }

        $record->update(['verified' => true]);

        return response()->json(['verified' => true], 200);
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
