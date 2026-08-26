<?php

namespace App\Models\Mail;

use GuzzleHttp\Client;
use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;

class ResetPassword extends Mailable
{
    use Queueable, SerializesModels;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct($user, $url)
    {
        $this->user = $user->name;
        $this->url = $url;
    }

    /**
     * Build the message.
     *
     * @return $this
     */
    public function build()
    {
        return $this->view('app.account.mail.resetPassword')
        ->subject(__('emails.resetPassword.subject'))
        ->with([
            'user' => $this->user,
            'url' => $this->url,
        ]);
    }
}
