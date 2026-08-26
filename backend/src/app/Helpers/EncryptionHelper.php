<?php

namespace App\Helpers;

class EncryptionHelper
{
    private const ALGORITHM = 'aes-256-gcm';

    /**
     * Decrypts a string using AES-256-GCM with the master key from .env
     *
     * @param string $encrypted Encrypted text in base64
     * @return string Decrypted plaintext
     * @throws \Exception If decryption fails
     */
    public static function decrypt(string $encrypted): string
    {
        $key = self::getMasterKey();
        $data = base64_decode($encrypted);

        if ($data === false) {
            throw new \Exception('Invalid base64 encrypted data');
        }

        $ivLength = openssl_cipher_iv_length(self::ALGORITHM);

        if (strlen($data) < $ivLength + 16) {
            throw new \Exception('Encrypted data is too short');
        }

        $iv = substr($data, 0, $ivLength);
        $tag = substr($data, $ivLength, 16);
        $ciphertext = substr($data, $ivLength + 16);

        $plaintext = openssl_decrypt(
            $ciphertext,
            self::ALGORITHM,
            $key,
            OPENSSL_RAW_DATA,
            $iv,
            $tag
        );

        if ($plaintext === false) {
            throw new \Exception('Decryption failed: ' . openssl_error_string());
        }

        return $plaintext;
    }

    /**
     * Gets the master key from configuration
     *
     * @return string Master key in raw format (32 bytes)
     * @throws \Exception If the key is not configured
     */
    private static function getMasterKey(): string
    {
        $key = config('encryption.master_key');

        if (empty($key)) {
            throw new \Exception('ENCRYPTION_MASTER_KEY not configured in .env');
        }
        
        if (str_starts_with($key, 'base64:')) {
            $decoded = base64_decode(substr($key, 7));
            if ($decoded === false || strlen($decoded) !== 32) {
                throw new \Exception('Invalid ENCRYPTION_MASTER_KEY format (must be 32 bytes)');
            }
            return $decoded;
        }

        if (strlen($key) !== 32) {
            throw new \Exception('ENCRYPTION_MASTER_KEY must be 32 bytes long');
        }

        return $key;
    }
}
