<?php

namespace App\Models\Mail;

use GuzzleHttp\Client;
use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;

class PasswordChanged extends Mailable
{
    use Queueable, SerializesModels;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct($user)
    {
        $this->user = $user->name;
    }

    /**
     * Build the message.
     *
     * @return $this
     */
    public function build()
    {
        return $this->view('app.account.mail.passwordChanged')
        ->subject(__('emails.passwordChanged.subject'))
        ->with([
            'user' => $this->user,
        ]);
    }
}
