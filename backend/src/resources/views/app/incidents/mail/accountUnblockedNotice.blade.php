<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html dir="ltr" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="{{ app()->getLocale() }}">
 <head>
  <meta charset="UTF-8">
  <meta content="width=device-width, initial-scale=1" name="viewport">
  <meta name="x-apple-disable-message-reformatting">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta content="telephone=no" name="format-detection">
  <title>{{ __('emails.accountUnblocked.title') }}</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900&display=swap">
 </head>
 <body class="body" style="width:100%;height:100%;padding:0;Margin:0">
  <div dir="ltr" lang="{{ app()->getLocale() }}" style="background-color:#F6F6F6">
   <table width="100%" cellspacing="0" cellpadding="0" role="none" style="border-collapse:collapse;border-spacing:0px;padding:0;Margin:0;width:100%;height:100%;background-color:#F6F6F6">
     <tr>
      <td valign="top" style="padding:0;Margin:0">
       <table cellspacing="0" cellpadding="0" align="center" role="none" style="border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important">
         <tr>
          <td align="center" style="padding:0;Margin:0">
           <table cellspacing="0" cellpadding="0" bgcolor="#ffffff" align="center" role="none" style="border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:600px">
             <tr>
              <td align="left" bgcolor="#12b76a" style="Margin:0;padding:30px 40px;background-color:#12b76a">
               <p style="Margin:0;font-family:Poppins, sans-serif;line-height:30px;letter-spacing:0;color:#FFFFFF;font-size:22px"><strong>{{ __('emails.accountUnblocked.heading') }}</strong></p>
              </td>
             </tr>
             <tr>
              <td align="left" style="Margin:0;padding:40px 40px 10px 40px">
               <p style="Margin:0;font-family:Poppins, sans-serif;line-height:27px;letter-spacing:0;color:#686868;font-size:18px">{{ !empty($user) ? __('emails.common.greeting', ['name' => $user]) : __('emails.common.greetingNoName') }}</p>
               <p style="Margin:16px 0 0 0;font-family:Poppins, sans-serif;line-height:24px;letter-spacing:0;color:#686868;font-size:16px">
                {!! __('emails.accountUnblocked.body') !!}
               </p>
               <p style="Margin:20px 0 0 0;font-family:Poppins, sans-serif;line-height:24px;letter-spacing:0;color:#686868;font-size:16px">
                {!! __('emails.accountUnblocked.rules') !!}
               </p>
               <p style="Margin:20px 0 0 0;font-family:Poppins, sans-serif;line-height:21px;letter-spacing:0;color:#9a9a9a;font-size:14px">
                {{ __('emails.common.noReply') }}
               </p>
              </td>
             </tr>
             <tr>
              <td align="left" style="Margin:0;padding:20px 40px 40px 40px">
               <p style="Margin:0;font-family:Poppins, sans-serif;line-height:24px;letter-spacing:0;color:#686868;font-size:16px">{{ __('emails.common.regards') }}</p>
               <p style="Margin:0;font-family:Poppins, sans-serif;line-height:24px;letter-spacing:0;color:#686868;font-size:16px">{{ __('emails.common.teamModeration') }}</p>
              </td>
             </tr>
             <tr>
              <td align="center" bgcolor="#5800c0" style="Margin:0;padding:30px 40px;background-color:#5800c0">
               <p style="Margin:0;font-family:Poppins, sans-serif;line-height:21px;letter-spacing:0;color:#f8f7fa;font-size:14px">{{ __('emails.common.copyright') }}</p>
              </td>
             </tr>
           </table></td>
         </tr>
       </table></td>
     </tr>
   </table>
  </div>
 </body>
</html>
