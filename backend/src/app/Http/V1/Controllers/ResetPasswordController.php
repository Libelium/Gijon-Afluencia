<?php

namespace App\Http\V1\Controllers;

use App\Traits\KeycloakHelper;
use App\Helpers\MailLocaleHelper;
use App\Http\V1\Controllers\Controller;
use App\Models\Mail\ResetPassword;
use App\Models\Mail\PasswordChanged;
use App\Models\PasswordReset;
use App\Models\User;

use Carbon\Carbon;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Mail;
use Illuminate\Support\Str;

class ResetPasswordController extends Controller
{
    use KeycloakHelper;

    public function resetLink(Request $request)
    {
        $request->validate([
            'email' => 'required|email',
        ]);

        $user = User::where('email', strtolower($request->email))->first();

        if (!$user) {
            return response(
                'MAL Your request has been processed. ' .
                    'If the email address is registered on the platform, ' .
                    'you will receive an email with the steps you have to follow to finish the operation.',
                200
            );
        }

        PasswordReset::where('email', '=', strtolower($request->email))->delete();

        $token = Str::random(60);

        PasswordReset::insert([
            'email' => strtolower($request->email),
            'token' => $token,
            'created_at' => date('Y-m-d H:i:s'),
        ]);

        $url = 'reset-password/' . $token . '?email=' . $request->email;
        // Render the email in the recipient's own language (falls back to English).
        Mail::to($request->email)
            ->locale(MailLocaleHelper::forUser($user))
            ->send(new ResetPassword($user, $url));

        return response(
            'Your request has been processed.' .
                ' If the email address is registered on the platform, ' .
                'you will receive an email with the steps you have to follow to finish the operation.',
            200
        );
    }

    public function changePassword(Request $request)
    {
        $request->validate([
            'token' => 'required',
            'email' => 'required|email',
            'password' => 'required|min:8|confirmed',
        ]);
        // Get the reset entry to ensure the token is valid and the reset has been requested
        $reset = PasswordReset::where('email', strtolower($request->email))
            ->where('token', $request->token)
            ->first();

        if (!$reset) {
            return response('Not found', 404);
        }

        //Check token expiration
        $created = Carbon::create($reset->created_at);
        $now = Carbon::now();

        if ($created->diffInMinutes($now) > 720) {
            // 720 = 12 hours
            return response('Token expired', 401);
        }

        // Get the user and change the password
        $user = User::where('email', strtolower($request->email))->first();


        $changed = $this->changeKeycloakPassword($user->keycloak_client_id, $request->password);
        if (!$changed)
            return response('Error changing password', 500);

        // enable the user again in case it was disabled
        $user->enabled = true;
        $user->save();

        // Delete the reset token
        PasswordReset::where('email', '=', strtolower($request->email))->delete();

        // Send the email
        Mail::to($request->email)
            ->locale(MailLocaleHelper::forUser($user))
            ->send(new PasswordChanged($user));

        return response('ok', 200);
    }


    public function updatePassword(Request $request)
    {
        // Validate the request
        $request->validate([
            'old_password' => 'required',
            'new_password' => 'required|min:8|confirmed',
        ]);
        // Get the logged user
        $user = auth()->user();

        // Check the old password
        if (!Hash::check($request->old_password, $user->password)) {
            return response('Invalid password', 400);
        }
        // Change the password in keycloak and in the database
        $changed = $this->changeKeycloakPassword($user->keycloak_client_id, $request->new_password);
        if (!$changed)
            return response('Error changing password', 500);

        $user->password = Hash::make($request->new_password);
        $user->save();

        // Return the response
        return response('ok', 200);
    }
}
