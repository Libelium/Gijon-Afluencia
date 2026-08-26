<?php

namespace App\Http\V1\Controllers;

use Firebase\JWT\JWT;
use Firebase\JWT\JWK;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use App\Models\TelegramUserChat;

class TelegramController extends Controller
{
    public function connect(Request $request): JsonResponse
    {
        $request->validate([
            'id_token' => ['required', 'string'],
        ]);

        try {
            $jwks = Cache::remember('telegram_jwks', 3600, function () {
                $response = Http::get('https://oauth.telegram.org/.well-known/jwks.json');
                return $response->json();
            });

            $keys = JWK::parseKeySet($jwks);

            $decoded = JWT::decode($request->input('id_token'), $keys);

            if (($decoded->iss ?? null) !== 'https://oauth.telegram.org') {
                return response()->json(['message' => 'Invalid token issuer'], 422);
            }

            if (($decoded->aud ?? null) !== config('services.telegram.client_id')) {
                return response()->json(['message' => 'Invalid token audience'], 422);
            }

            $chatId = (int) $decoded->id;

        } catch (\Exception $e) {
            return response()->json(['message' => 'Invalid token: ' . $e->getMessage()], 422);
        }

        $user = Auth::user();

        TelegramUserChat::updateOrCreate(
            ['user_id' => $user->id],
            [
                'chat_id' => (int) $decoded->id,
                'name'    => $this->maskName($decoded->name),
            ]
        );

        return response()->json([
            'status' => 'connected',
            'chat_id' => $chatId,
        ]);
    }

    private function maskName(string $name): string
    {
        $len = mb_strlen($name);

        if ($len <= 1) {
            return $name;
        }

        if ($len === 2) {
            return mb_substr($name, 0, 1) . '*';
        }

        $middle = str_repeat('*', $len - 2);

        return mb_substr($name, 0, 1) . $middle . mb_substr($name, -1);
    }

    public function disconnect(): JsonResponse
    {
        TelegramUserChat::where('user_id', Auth::id())->delete();

        return response()->json(['status' => 'disconnected']);
    }

    public function status(): JsonResponse
    {
        $chat = TelegramUserChat::where('user_id', Auth::id())->first();

        return response()->json([
            'status'  => $chat ? 'connected' : 'not_connected',
            'chat_id' => $chat ? (int) $chat->chat_id : null,
            'name'    => $chat ? $chat->name : null,
        ]);
    }

    public function config(): JsonResponse
    {
        return response()->json([
            'client_id' => config('services.telegram.client_id'),
        ]);
    }
}
